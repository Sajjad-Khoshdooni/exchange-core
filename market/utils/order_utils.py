import logging
from collections import defaultdict
from decimal import Decimal
from typing import Union
from uuid import UUID

from django.db.models import Max, Min, F, Q, OuterRef, Subquery, DecimalField, Sum
from django.utils import timezone

from accounts.models import Account
from ledger.models import Wallet, Asset
from ledger.utils.external_price import BUY, SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, PairSymbol, StopLoss
from market.models.order import CancelOrder
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
              time_in_force: str = Order.GTC, pass_min_notional: bool = False) -> Union[Order, None]:
    wallet = symbol.asset.get_wallet(account, market=market)
    if fill_type == Order.MARKET:
        price = Order.get_market_price(symbol, Order.get_opposite_side(side))
        if not price:
            if raise_exception:
                raise Exception('Empty order book')
            else:
                logger.info('new order failed: empty order book %s' % symbol)
                return

    base_asset_symbol = symbol.base_asset.symbol

    if not pass_min_notional:
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
            account=account,
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
        matched_trades = order.submit(pipeline, is_stop_loss=is_stop_loss) or ([], [])

    extra = {} if matched_trades.trade_pairs else {'side': order.side}
    MarketStreamCache().execute(symbol, matched_trades.filled_orders, trade_pairs=matched_trades.trade_pairs, **extra)
    return order


def trigger_stop_loss(stop_loss: StopLoss, triggered_price: Decimal):
    try:
        if stop_loss.price:
            order = new_order(
                stop_loss.symbol, stop_loss.wallet.account, stop_loss.unfilled_amount, stop_loss.price, stop_loss.side,
                Order.LIMIT, raise_exception=False, market=stop_loss.wallet.market,
                parent_lock_group_id=stop_loss.group_id
            )
        else:
            order = new_order(
                stop_loss.symbol, stop_loss.wallet.account, stop_loss.unfilled_amount, None, stop_loss.side,
                Order.MARKET, raise_exception=False, market=stop_loss.wallet.market,
                parent_lock_group_id=stop_loss.group_id
            )
    except Exception:
        order = None
    if not order:
        logger.exception(f'could not place order for stop loss ({stop_loss.symbol})',
                         extra={
                             'triggered_price': triggered_price,
                             'stop_loss': stop_loss.id,
                             'stop_loss_side': stop_loss.side,
                             'stop_loss_trigger_price': stop_loss.trigger_price,
                         })
        if stop_loss.fill_type == StopLoss.MARKET:
            stop_loss.canceled_at = timezone.now()
            stop_loss.save(update_fields=['canceled_at'])
        return

    order.refresh_from_db()
    order.stop_loss = stop_loss
    order.save(update_fields=['stop_loss_id'])
    stop_loss.filled_amount += order.filled_amount
    stop_loss.save(update_fields=['filled_amount'])
    logger.info(f'filled order at {triggered_price} with amount: {order.filled_amount}, price: {order.price} for '
                f'stop loss({stop_loss.id}) {stop_loss.filled_amount} {stop_loss.trigger_price} {stop_loss.price} '
                f'{stop_loss.side} ')


def get_market_top_prices(order_type='all', symbol_ids=None):
    market_top_prices = defaultdict(lambda: Decimal())
    symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
    if order_type != 'all':
        symbol_filter['type'] = order_type
    for depth in Order.open_objects.filter(**symbol_filter).values('symbol', 'side').annotate(
            max_price=Max('price'), min_price=Min('price')):
        market_top_prices[
            (depth['symbol'], depth['side'])
        ] = (depth['max_price'] if depth['side'] == BUY else depth['min_price']) or Decimal()
    return market_top_prices


def get_market_top_price_amounts(order_types_in=None, symbol_ids=None):
    market_top_price_amounts = defaultdict(lambda: {'price': Decimal(), 'amount': Decimal()})
    symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
    if order_types_in:
        symbol_filter['type__in'] = order_types_in
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
        Q(price=F('max_price'), side=BUY) | Q(price=F('min_price'), side=SELL)
    ).annotate(total_amount=Sum('amount')):
        market_top_price_amounts[(depth['symbol'], depth['side'])] = {
            'price': depth['max_price'] if depth['side'] == BUY else depth['min_price'],
            'amount': depth['total_amount'],
        }
    return market_top_price_amounts
