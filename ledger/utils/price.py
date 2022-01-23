from datetime import datetime
from decimal import Decimal

from cachetools import TTLCache

from collector.grpc_client import gRPCClient
from ledger.models import Asset
from ledger.utils.cache import ttl_cache

cache = TTLCache(maxsize=1000, ttl=2)

BINANCE = 'binance'
NOBITEX = 'nobitex'

MARKET_USDT = 'USDT'
MARKET_IRT = 'IRT'

BUY, SELL = 'buy', 'sell'


def get_other_side(side: str):
    assert side in (BUY, SELL)

    return BUY if side == SELL else SELL


@ttl_cache(cache)
def get_price(coin: str, side: str, exchange: str = BINANCE, market_symbol: str = MARKET_USDT,
              now: datetime = None) -> Decimal:

    if coin == 'USDT' and exchange == BINANCE:
        return Decimal('1')

    if coin == 'IRT':
        return Decimal('0')

    if not now:
        now = datetime.now()

    if exchange == BINANCE:
        delay = 60_000
    else:
        delay = 600_000

    grpc_client = gRPCClient()
    timestamp = int(now.timestamp() * 1000) - delay

    orders = grpc_client.get_current_orders(
        exchange=exchange,
        symbols=(coin + market_symbol,),
        position=0,
        type=side,
        timestamp=timestamp,
        order_by=('symbol', 'position', '-timestamp'),
        distinct=('symbol',),
        values=('symbol', 'price')
    ).orders

    if orders:
        price = orders[0].price
    else:
        price = 0

    grpc_client.channel.close()

    return Decimal(price)


def get_tether_irt_price(side: str,now: datetime = None) -> Decimal:
    tether_rial = get_price('USDT', side=side, exchange=NOBITEX, market_symbol=MARKET_IRT, now=now)
    return Decimal(tether_rial / 10)


def get_all_assets_prices(side: str, now: datetime = None):
    prices = {}

    for asset in Asset.objects.all():
        prices[asset.symbol] = Decimal(get_price(asset.symbol, side, now=now))

    return prices


def get_trading_price(coin: str, side: str):
    assert coin != MARKET_IRT

    # other_side = get_other_side(side)
    diff = Decimal('0.005')

    if side == BUY:
        multiplier = 1 + diff
    else:
        multiplier = 1 - diff

    price = get_price(coin, side) * get_tether_irt_price(side)

    return price * multiplier
