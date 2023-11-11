import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Union

from django.conf import settings
from django.utils import timezone
from redis import Redis

logger = logging.getLogger(__name__)

price_redis = Redis.from_url(settings.PRICE_CACHE_LOCATION, decode_responses=True)


BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

SIDES = BUY, SELL = 'buy', 'sell'
LONG, SHORT = 'long', 'short'

SIDE_VERBOSE = {
    BUY: 'خرید',
    SELL: 'فروش'
}

DAY = 24 * 3600


def _get_redis_side(side: str):
    assert side in (BUY, SELL)
    return 'a' if side == SELL else 'b'


def get_other_side(side: str):
    assert side in (BUY, SELL)

    return BUY if side == SELL else SELL


@dataclass
class Price:
    coin: str
    price: Decimal
    side: str


SIDE_MAP = {
    BUY: 'b',
    SELL: 'a'
}


def _get_redis_price_key(coin: str, market: str = None):
    prefix = 'price:'
    if market:
        prefix = prefix + 'f:'

    base = 'usdt'

    return prefix + coin.lower() + base


def _check_price_dict_time_frame(data: dict, allow_stale: bool = False):
    now = timezone.now().timestamp()
    return allow_stale or not data.get('t') or now - 30 <= float(data.get('t')) <= now


def fetch_external_price(symbol, side: str, allow_stale: bool = False) -> Decimal:
    side = _get_redis_side(side)
    name = f'price:{symbol.lower()}'
    price = price_redis.hget(name=name, key=side)

    if not price and allow_stale:
        name += ':stale'
        price = price_redis.hget(name=name, key=side)

    if price:
        return Decimal(price)


def fetch_external_redis_prices(coins: Union[list, set], side: str = None, allow_stale: bool = False) -> List[Price]:
    results = []

    if side:
        sides = [side]
    else:
        sides = SIDES

    pipe = price_redis.pipeline(transaction=False)
    for c in coins:
        key = _get_redis_price_key(c)
        pipe.hgetall(key)

        key = _get_redis_price_key(c, market='futures')
        pipe.hgetall(key)

    prices = pipe.execute()

    for i, c in enumerate(coins):
        spot_price_dict = prices[2 * i] or {}
        futures_price_dict = prices[2 * i + 1] or {}

        if allow_stale and not spot_price_dict:
            name = _get_redis_price_key(c) + ':stale'
            spot_price_dict = price_redis.hgetall(name)

            # logger.error('{} price fallback to stale'.format(c))

        for s in sides:
            _prices = []

            spot_price = spot_price_dict.get(SIDE_MAP[s])
            if spot_price is not None and _check_price_dict_time_frame(spot_price_dict, allow_stale=allow_stale):
                _prices.append(Decimal(spot_price))

            futures_price = futures_price_dict.get(SIDE_MAP[s])

            if futures_price is not None and _check_price_dict_time_frame(futures_price_dict, allow_stale=allow_stale):
                _prices.append(Decimal(futures_price))

            if not _prices:
                continue

            func = min if s == BUY else max

            results.append(
                Price(coin=c, price=func(_prices), side=s)
            )

    return results


def fetch_external_depth(symbol: str, side: str) -> str:
    key = _get_redis_side(side)
    data = price_redis.hgetall(name=f'depth:{symbol.lower()}')

    if data and _check_price_dict_time_frame(data):
        return data[key]
