import logging
from collections import defaultdict
from decimal import Decimal
from typing import Union
from uuid import UUID

from django.db.models import Max, Min, F, Q, OuterRef, Subquery, DecimalField, Sum

from accounts.models import Account
from ledger.models import Wallet, Asset
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, PairSymbol
from market.utils.redis import MarketStreamCache

logger = logging.getLogger(__name__)


class MinTradeError(Exception):
    pass


class MaxTradeError(Exception):
    pass


class MinNotionalError(Exception):
    pass


def new_order(symbol: PairSymbol, account: Account, amount: Decimal, price: Decimal, side: str,
              fill_type: str = Order.LIMIT, raise_exception: bool = True, market: str = Wallet.SPOT,
              order_type: str = Order.ORDINARY, parent_lock_group_id: Union[UUID, None] = None,
              time_in_force: str = Order.GTC) -> Union[Order, None]:

    wallet = symbol.asset.get_wallet(account, market=market)
    if fill_type == Order.MARKET:
        price = Order.get_market_price(symbol, Order.get_opposite_side(side))
        if not price:
            if raise_exception:
                raise Exception('Empty order book')
            else:
                logger.info('new order failed: empty order book %s' % symbol)
                return

    if amount < symbol.min_trade_quantity:
        if raise_exception:
            raise MinTradeError
        else:
            logger.info(
                'new order failed: min_trade_quantity %s (%s < %s)' % (symbol, amount, symbol.min_trade_quantity))
            return

    if amount > symbol.max_trade_quantity:
        if raise_exception:
            raise MinTradeError
        else:
            logger.info('new order failed: max_trade_quantity')
            return

    base_asset_symbol = symbol.base_asset.symbol

    if base_asset_symbol == Asset.IRT:
        min_notional = Order.MIN_IRT_ORDER_SIZE
    elif base_asset_symbol == Asset.USDT:
        min_notional = Order.MIN_USDT_ORDER_SIZE
    else:
        raise NotImplementedError

    if amount * price < min_notional:
        if raise_exception:
            raise MinNotionalError
        else:
            logger.info('new order failed: min_notional')
            return
    with WalletPipeline() as pipeline:
        additional_params = {'group_id': parent_lock_group_id} if parent_lock_group_id else {}
        order = Order.objects.create(
            wallet=wallet,
            symbol=symbol,
            amount=amount,
            price=price,
            side=side,
            fill_type=fill_type,
            type=order_type,
            time_in_force=time_in_force,
            **additional_params
        )

        is_stop_loss = parent_lock_group_id is not None
        trade_pairs, updated_orders = order.submit(pipeline, is_stop_loss=is_stop_loss) or ([], [])

    extra = {} if trade_pairs else {'side': order.side}
    MarketStreamCache().execute(symbol, updated_orders, trade_pairs=trade_pairs, **extra)
    return order


def get_market_top_prices(order_type='all', symbol_ids=None):
    market_top_prices = defaultdict(lambda: Decimal())
    symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
    if order_type != 'all':
        symbol_filter['type'] = order_type
    for depth in Order.open_objects.filter(**symbol_filter).values('symbol', 'side').annotate(
            max_price=Max('price'), min_price=Min('price')):
        market_top_prices[
            (depth['symbol'], depth['side'])
        ] = (depth['max_price'] if depth['side'] == Order.BUY else depth['min_price']) or Decimal()
    return market_top_prices


def get_market_top_price_amounts(order_type='all', symbol_ids=None):
    market_top_price_amounts = defaultdict(lambda: {'price': Decimal(), 'amount': Decimal()})
    symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
    if order_type != 'all':
        symbol_filter['type'] = order_type
    sub_query = Order.open_objects.filter(
        **symbol_filter,
        symbol=OuterRef('symbol'),
        side=OuterRef('side'),
    )
    for depth in Order.open_objects.filter(**symbol_filter).values('symbol', 'side').annotate(
            min_price=Subquery(
                sub_query.order_by('price').values_list('price')[:1],
                output_field=DecimalField(),
            ),
            max_price=Subquery(
                sub_query.order_by('-price').values_list('price')[:1],
                output_field=DecimalField(),
            )
    ).filter(
        Q(price=F('max_price'), side=Order.BUY) | Q(price=F('min_price'), side=Order.SELL)
    ).annotate(total_amount=Sum('amount')):
        market_top_price_amounts[(depth['symbol'], depth['side'])] = {
            'price': depth['max_price'] if depth['side'] == Order.BUY else depth['min_price'],
            'amount': depth['total_amount'],
        }
    return market_top_price_amounts
