import logging
import random
from collections import defaultdict
from decimal import Decimal
from time import time

from django.db.models import Max, Min

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.precision import floor_precision
from ledger.utils.price import get_trading_price_irt, get_trading_price_usdt, SELL, BUY
from market.models import PairSymbol, Order
from market.utils import new_order
from market.utils.order_utils import get_market_top_prices, cancel_orders

logger = logging.getLogger(__name__)


def get_current_price(symbol: PairSymbol, side: str) -> Decimal:
    if symbol.name.endswith(Asset.IRT):
        base_symbol = Asset.IRT
        get_trading_price = get_trading_price_irt
    elif symbol.name.endswith(Asset.USDT):
        base_symbol = Asset.USDT
        get_trading_price = get_trading_price_usdt
    else:
        raise NotImplementedError

    coin = symbol.name.split(base_symbol)[0]
    return get_trading_price(coin, side)


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


def random_buy(symbol: PairSymbol, account: Account, max_amount, daily_factor: int):
    amount_value = random_min_order_value(symbol, daily_factor)
    ask = get_current_price(symbol, SELL)
    amount = floor_precision(min(max_amount, Decimal(amount_value / ask)), symbol.step_size)

    return new_order(
        symbol, account, amount, None, side=BUY, fill_type=Order.MARKET, raise_exception=False, order_type=Order.BOT
    )


def random_sell(symbol: PairSymbol, account: Account, max_amount, daily_factor: int):
    wallet = symbol.asset.get_wallet(account)
    balance = wallet.get_free()

    bid = get_current_price(symbol, BUY)

    balance = min(balance, min(max_amount, random_min_order_value(symbol, daily_factor) / bid))
    amount = floor_precision(balance, symbol.step_size)

    return new_order(
        symbol, account, amount, None, fill_type=Order.MARKET, side=SELL, raise_exception=False, order_type=Order.BOT
    )


def balance_tether(account: Account):
    usdt_wallet = Asset.get(Asset.USDT).get_wallet(account)
    irt_wallet = Asset.get(Asset.IRT).get_wallet(account)

    usdt, irt = usdt_wallet.get_free(), irt_wallet.get_free()

    usdt_irt_price = get_trading_price_irt(Asset.USDT, SELL, raw_price=True)

    total_usdt = usdt + irt / usdt_irt_price

    if total_usdt < 100:
        logger.warning('Small free balance in account=%s' % account)
        return

    if usdt / total_usdt < Decimal('0.2'):
        to_buy_usdt = total_usdt * Decimal('0.45') - usdt

        pair = PairSymbol.objects.get(name='USDTIRT')
        amount = floor_precision(to_buy_usdt, pair.step_size)

        return new_order(pair, account, amount, None, side=BUY, fill_type=Order.MARKET, raise_exception=False,
                         order_type=Order.BOT)


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
        (o['symbol'], o['side']): o['max_price'] if o['side'] == Order.BUY else o['min_price'] for o in
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
    cancel_orders(Order.open_objects.filter(wallet__account=account, symbol=symbol, side=side))
    min_precision = Order.get_rounding_precision(top_user_price, symbol.tick_size)
    random_precision = random.randint(min_precision, symbol.tick_size)

    one_tick_price = Decimal(f'1e{-random_precision}')
    new_top_price = top_user_price + one_tick_price if side == Order.BUY else top_user_price - one_tick_price
    if top_opposite_user_price and (
            (side == Order.BUY and new_top_price >= top_opposite_user_price) or (
            side == Order.SELL and new_top_price <= top_opposite_user_price)
    ):
        logger.info(f'no need to place carrot order on {symbol} {new_top_price} {top_opposite_user_price}')
        return
    amount = floor_precision(symbol.maker_amount / get_time_based_factor(600) / 5, symbol.step_size)
    return new_order(
        symbol, account, amount, new_top_price, side=side, fill_type=Order.LIMIT, raise_exception=False,
        order_type=Order.BOT
    )