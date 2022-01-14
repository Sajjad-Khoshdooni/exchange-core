from datetime import datetime

from cachetools import TTLCache

from collector.grpc_client import gRPCClient
from ledger.models import Asset, Order
from decimal import Decimal

from ledger.utils.cache import ttl_cache

EXCHANGE_BINANCE = 'binance'
EXCHANGE_NOBITEX = 'nobitex'

MARKET_USDT = 'USDT'
MARKET_IRT = 'IRT'

cache = TTLCache(maxsize=1000, ttl=10)


@ttl_cache(cache)
def get_price(coin: str, exchange: str = EXCHANGE_BINANCE, market_symbol: str = MARKET_USDT,
              timedelta_multiplier: int = 1, now: datetime = None) -> Decimal:

    _now = now
    if not now:
        _now = datetime.now()
    else:
        timedelta_multiplier *= 2

    grpc_client = gRPCClient()
    max_timestamp = int(_now.timestamp() * 1000)
    min_timestamp = max_timestamp - 5_000 * timedelta_multiplier

    price = grpc_client.get_trades_average_price_by_time(
        exchange=exchange,
        symbol=coin + market_symbol,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
    ).value

    if not price and not now:
        print('price fallback to last trade in %s, %s, %s' % (coin, exchange, market_symbol))

        if not now:
            _now = datetime.now()

        timestamp = int(_now.timestamp() * 1000) - 60_000

        trades = grpc_client.get_current_trades(
            exchange=exchange,
            symbols=(coin + market_symbol,),
            timestamp=timestamp,
            order_by=('-timestamp',),
            limit=1
        ).trades

        if trades:
            price = trades[0].price

    grpc_client.channel.close()

    return Decimal(price)


def get_tether_irt_price(now: datetime = None) -> Decimal:
    tether_rial = get_price('USDT', exchange=EXCHANGE_NOBITEX, market_symbol=MARKET_IRT, timedelta_multiplier=6, now=now)
    return Decimal(tether_rial / 10)


def get_all_assets_prices(now: datetime = None):
    prices = {}

    for asset in Asset.objects.all():
        prices[asset.symbol] = Decimal(get_price(asset.symbol, now=now))

    return prices


def get_trading_price(coin: str, side: str):
    diff = Decimal('0.005')

    if side == Order.BUY:
        multiplier = 1 + diff
    else:
        multiplier = 1 - diff

    price = get_price(coin) * get_tether_irt_price()

    return price * multiplier
