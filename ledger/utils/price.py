from datetime import datetime
from decimal import Decimal
from typing import Dict

from cachetools import TTLCache

from collector.price.grpc_client import gRPCClient
from ledger.utils.cache import ttl_cache
from ledger.utils.price_manager import PriceManager

cache = TTLCache(maxsize=1000, ttl=0.5)

BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'


def get_other_side(side: str):
    assert side in (BUY, SELL)

    return BUY if side == SELL else SELL


def get_prices_dict(coins: list, side: str, exchange: str = BINANCE, market_symbol: str = USDT,
                    now: datetime = None) -> Dict[str, Decimal]:

    extra = {}

    if exchange == BINANCE and USDT in coins:
        extra[USDT] = Decimal(1)
        coins.remove(USDT)

    if IRT in coins:
        extra[IRT] = Decimal(0)
        coins.remove(IRT)

    if not coins:
        return extra

    symbol_to_coins = {
        c + market_symbol: c for c in coins
    }

    if not now:
        _now = datetime.now()
    else:
        _now = now

    if exchange == BINANCE:
        delay = 60_000
    else:
        delay = 600_000

    grpc_client = gRPCClient()
    timestamp = int(_now.timestamp() * 1000) - delay

    orders = grpc_client.get_current_orders(
        exchange=exchange,
        symbols=tuple(symbol_to_coins.keys()),
        position=0,
        type=side,
        timestamp=timestamp,
        order_by=('symbol', '-timestamp'),
        distinct=('symbol',),
        values=('symbol', 'price')
    ).orders

    grpc_client.channel.close()

    result = {
        symbol_to_coins[o.symbol]: Decimal(o.price) for o in orders
    }

    result.update(extra)

    if PriceManager.active():
        for (coin, price) in result.items():
            PriceManager.set_price(coin, side, exchange, market_symbol, now, price)

    return result


@ttl_cache(cache)
def get_price(coin: str, side: str, exchange: str = BINANCE, market_symbol: str = USDT,
              now: datetime = None) -> Decimal:

    if PriceManager.active():
        price = PriceManager.get_price(coin, side, exchange, market_symbol, now)
        if price is not None:
            return price

    prices = get_prices_dict([coin], side, exchange, market_symbol, now)

    if prices:
        return prices[coin]
    else:
        return Decimal(0)


def get_tether_irt_price(side: str, now: datetime = None) -> Decimal:
    tether_rial = get_price('USDT', side=side, exchange=NOBITEX, market_symbol=IRT, now=now)
    return Decimal(tether_rial / 10)


def get_trading_price_usdt(coin: str, side: str, raw_price: bool = False) -> Decimal:
    assert coin != IRT
    diff = Decimal('0.005')

    if raw_price:
        multiplier = 1
    else:
        if side == BUY:
            multiplier = 1 - diff
        else:
            multiplier = 1 + diff

    price = get_price(coin, side)

    return price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False) -> Decimal:
    if coin == IRT:
        return Decimal(1)

    return get_trading_price_usdt(coin, side, raw_price) * get_tether_irt_price(side)


def get_presentation_amount(amount: Decimal, precision: int):
    if isinstance(amount, str):
        amount = Decimal(amount)

    rounded = str(round(amount, precision))

    if '.' not in rounded:
        return rounded
    else:
        return rounded.rstrip('0').rstrip('.') or '0'
