import logging
import random
from decimal import Decimal

from accounts.models import Account
from ledger.models import Asset
from ledger.utils.precision import floor_precision
from ledger.utils.price import get_trading_price_irt, get_trading_price_usdt, SELL, BUY
from market.models import PairSymbol, Order
from market.utils import new_order

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


def random_min_order_value(base_symbol: str) -> Decimal:
    min_order = min_order_value(base_symbol)
    return Decimal(random.randint(2 * min_order, 3 * min_order))


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


def random_buy(symbol: PairSymbol, account: Account):
    amount_value = random_min_order_value(symbol.base_asset.symbol)
    ask = get_current_price(symbol, SELL)
    amount = floor_precision(Decimal(amount_value / ask), symbol.step_size)

    if not is_all_system(symbol, SELL, amount):
        logger.info('buy ignored due to user top')
        return

    price = floor_precision(ask * Decimal('1.03'), symbol.tick_size)

    if amount * price < min_order_value(symbol.base_asset.symbol):
        logger.info('buy ignored due to small amount')
        return

    return new_order(symbol, account, amount, price, side=BUY, raise_exception=False, check_balance=False)


def random_sell(symbol: PairSymbol, account: Account):
    wallet = symbol.asset.get_wallet(account)
    balance = wallet.get_free()

    bid = get_current_price(symbol, BUY)

    balance = min(balance, random_min_order_value(symbol.base_asset.symbol) / bid)
    amount = floor_precision(balance, symbol.step_size)

    if not is_all_system(symbol, BUY, amount):
        logger.info('sell ignored due to user top')
        return

    price = floor_precision(bid * Decimal('0.97'), symbol.tick_size)

    if amount * price < min_order_value(symbol.base_asset.symbol):
        logger.info('sell ignored due to small amount')
        return

    return new_order(symbol, account, amount, price, side=SELL, raise_exception=False, check_balance=False)


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

        return new_order(pair, account, amount, None, side=BUY, fill_type=Order.MARKET, raise_exception=False)
