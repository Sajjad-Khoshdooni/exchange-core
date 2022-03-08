from datetime import datetime
from decimal import Decimal
from typing import Dict

from cachetools.func import ttl_cache

from collector.price.grpc_client import gRPCClient
# from ledger import models
from ledger.utils.price_manager import PriceManager

BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'


def get_other_side(side: str):
    assert side in (BUY, SELL)

    return BUY if side == SELL else SELL


def get_prices_dict(coins: list, side: str = None, exchange: str = BINANCE, market_symbol: str = USDT,
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

    if side:
        order_by = ('symbol', '-timestamp')
        distinct = ('symbol',)
        values = ('symbol', 'price')
    else:
        order_by = ('symbol', 'type', '-timestamp')
        distinct = ('symbol', 'type')
        values = ('symbol', 'type', 'price')

    orders = grpc_client.get_current_orders(
        exchange=exchange,
        symbols=tuple(symbol_to_coins.keys()),
        position=0,
        type=side,
        timestamp=timestamp,
        order_by=order_by,
        distinct=distinct,
        values=values,
    ).orders

    grpc_client.channel.close()

    result = {
        symbol_to_coins[o.symbol]: Decimal(o.price) for o in orders
    }

    result.update(extra)

    if PriceManager.active():
        for order in orders:
            coin = symbol_to_coins[order.symbol]
            _side = side

            if not _side:
                _side = order.type

            PriceManager.set_price(coin, _side, exchange, market_symbol, now, Decimal(order.price))

    return result


@ttl_cache(maxsize=1000, ttl=0.5)
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
    from ledger.models.asset import Asset
    assert coin != IRT
    asset = Asset.objects.get(symbol=coin)
    buy_diff = asset.buy_diff or Decimal('0.005')
    sell_diff = asset.sell_diff or Decimal('0.005')
    if raw_price:
        multiplier = 1
    else:
        if side == BUY:
            multiplier = 1 - buy_diff
        else:
            multiplier = 1 + sell_diff

    price = get_price(coin, side)

    return price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False) -> Decimal:
    if coin == IRT:
        return Decimal(1)

    return get_trading_price_usdt(coin, side, raw_price) * get_tether_irt_price(side)
