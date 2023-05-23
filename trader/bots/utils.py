import logging
import random
from collections import defaultdict
from decimal import Decimal
from time import time

from django.db import transaction
from django.db.models import Max, Min

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.external_price import get_external_price, BUY, SELL
from ledger.utils.precision import floor_precision
from market.models import PairSymbol, Order
from market.utils.order_utils import get_market_top_prices, new_order

logger = logging.getLogger(__name__)


def get_current_price(symbol: PairSymbol, side: str) -> Decimal:
    if symbol.name.endswith(Asset.IRT):
        base_coin = Asset.IRT
    elif symbol.name.endswith(Asset.USDT):
        base_coin = Asset.USDT
    else:
        raise NotImplementedError

    coin = symbol.name.split(base_coin)[0]
    return get_external_price(coin=coin, base_coin=base_coin, side=side)


def min_order_value(base_symbol: str):
    if base_symbol == Asset.IRT:
        return Order.MIN_IRT_ORDER_SIZE
    else:
        return Order.MIN_USDT_ORDER_SIZE


def random_min_order_value(symbol: PairSymbol, daily_factor) -> Decimal:
    min_order = min_order_value(symbol.base_asset.symbol)
    return Decimal(random.randint(2 * min_order, 8 * min_order)) * daily_factor


def get_top_orders(symbol: PairSymbol, side: str):
    orders = Order.open_objects.filter(symbol=symbol, side=side, fill_type=Order.LIMIT)

    if side == BUY:
        orders = orders.order_by('-price', 'id')
    else:
        orders = orders.order_by('price', 'id')

    return orders


def is_all_system(symbol: PairSymbol, side: str, amount: Decimal):
    orders = get_top_orders(symbol, side).prefetch_related('wallet__account')[:3]

    sum_amount = 0

    for o in orders:
        if not o.wallet.account.is_system():
            return False

        sum_amount += o.amount

        if sum_amount >= amount:
            return True

    return False


def random_buy(symbol: PairSymbol, account: Account, max_amount, market_price, daily_factor: int):
    ask = get_current_price(symbol, SELL)
    if market_price > ask * Decimal('1.01'):
        from market.models.order import CancelOrder
        msg = f'random-buy: Invalid market price {symbol} ({market_price}, {ask})'
        logger.info(msg)
        raise CancelOrder(msg)

    amount_value = random_min_order_value(symbol, daily_factor)
    amount = floor_precision(min(max_amount, Decimal(amount_value / ask)), symbol.step_size)

    return new_order(
        symbol, account, amount, market_price, side=BUY, fill_type=Order.LIMIT, raise_exception=False,
        order_type=Order.BOT, time_in_force=Order.IOC
    )


def random_sell(symbol: PairSymbol, account: Account, max_amount, market_price, daily_factor: int):
    bid = get_current_price(symbol, BUY)
    if market_price < bid * Decimal('0.99'):
        from market.models.order import CancelOrder
        msg = f'random-sell: Invalid market price {symbol} ({market_price}, {bid})'
        logger.info(msg)
        raise CancelOrder(msg)

    amount = floor_precision(min(max_amount, random_min_order_value(symbol, daily_factor) / bid), symbol.step_size)
    logger.info(f'random sell {symbol}, {amount}')
    return new_order(
        symbol, account, amount, market_price, fill_type=Order.LIMIT, side=SELL, raise_exception=False,
        order_type=Order.BOT, time_in_force=Order.IOC
    )


def user_top_prices(symbol_ids=None):
    symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
    return Order.open_objects.filter(
        **symbol_filter,
        type=Order.ORDINARY
    ).values('symbol', 'side').annotate(max_price=Max('price'), min_price=Min('price'))


def get_top_prices_exclude_system_orders(symbol_ids=None):
    no_filter_top_prices = get_market_top_prices(symbol_ids=symbol_ids)
    top_ordinary_prices = defaultdict(lambda: Decimal())

    user_orders = {
        (o['symbol'], o['side']): o['max_price'] if o['side'] == BUY else o['min_price'] for o in
        user_top_prices(symbol_ids)
    }
    for key, top_price in no_filter_top_prices.items():
        if top_price == user_orders.get(key):
            top_ordinary_prices[key] = top_price
    return top_ordinary_prices


def get_time_based_factor(interval):
    # returns one of (1, 2, 3, 5) for interval in seconds
    rounded_time = int(time()) // interval * interval
    return 1 + (rounded_time * rounded_time) % 7


def place_carrot_order(symbol: PairSymbol, account: Account, side, top_user_price, top_opposite_user_price):
    with transaction.atomic():
        Order.cancel_orders(Order.open_objects.filter(wallet__account=account, symbol=symbol, side=side))

    min_precision = Order.get_rounding_precision(top_user_price, symbol.tick_size)
    random_precision = random.randint(min_precision, symbol.tick_size)

    one_tick_price = Decimal(f'1e{-random_precision}')
    new_top_price = top_user_price + one_tick_price if side == BUY else top_user_price - one_tick_price
    if top_opposite_user_price and (
            (side == BUY and new_top_price >= top_opposite_user_price) or (
            side == SELL and new_top_price <= top_opposite_user_price)
    ):
        logger.info(f'no need to place carrot order on {symbol} {new_top_price} {top_opposite_user_price}')
        return
    amount = floor_precision(symbol.maker_amount / get_time_based_factor(600) / 5, symbol.step_size)
    return new_order(
        symbol, account, amount=amount, price=new_top_price, side=side, fill_type=Order.LIMIT, raise_exception=False,
        order_type=Order.BOT
    )
