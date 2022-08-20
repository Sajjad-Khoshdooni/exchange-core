import logging
from collections import defaultdict
from decimal import Decimal
from typing import Union

from django.db import transaction
from django.db.models import Max, Min

from accounts.models import Account
from ledger.models import Wallet, Asset
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, CancelRequest, PairSymbol

logger = logging.getLogger(__name__)


def cancel_order(order: Order) -> CancelRequest:
    request = CancelRequest.objects.create(order=order)
    order.cancel()

    return request


def cancel_orders(orders):
    if not orders:
        return

    with transaction.atomic():
        for order in orders:
            CancelRequest.objects.create(order=order)
            order.cancel()


def get_open_orders(wallet: Wallet):
    return Order.open_objects.filter(
        wallet=wallet,
    )


class MinTradeError(Exception):
    pass


class MaxTradeError(Exception):
    pass


class MinNotionalError(Exception):
    pass


def new_order(symbol: PairSymbol, account: Account, amount: Decimal, price: Decimal, side: str,
              fill_type: str = Order.LIMIT, raise_exception: bool = True, market: str = Wallet.SPOT,
              check_balance: bool = False, order_type: str = Order.ORDINARY) -> Union[Order, None]:

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
            logger.info('new order failed: min_trade_quantity %s (%s < %s)' % (symbol, amount, symbol.min_trade_quantity))
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
        order = Order.objects.create(
            wallet=wallet,
            symbol=symbol,
            amount=amount,
            price=price,
            side=side,
            fill_type=fill_type,
            type=order_type,
        )

        order.submit(pipeline, check_balance=check_balance)

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
