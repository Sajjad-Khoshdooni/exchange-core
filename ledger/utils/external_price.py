import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError
from typing import Dict, List, Union

import requests
from django.conf import settings
from django.core.cache import cache
from redis import Redis

from ledger.utils.cache import cache_for

logger = logging.getLogger(__name__)

price_redis = Redis.from_url(settings.PRICE_CACHE_LOCATION, decode_responses=True)


BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'

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


def _get_redis_price_key(coin: str):
    base = 'usdt'
    return 'price:' + coin.lower() + base


def _fetch_redis_prices(coins: list, side: str = None, allow_stale: bool = False) -> List[Price]:
    results = []

    if side:
        sides = [side]
    else:
        sides = [BUY, SELL]

    pipe = price_redis.pipeline(transaction=False)
    for c in coins:
        name = _get_redis_price_key(c)
        pipe.hgetall(name)

    prices = pipe.execute()

    for i, c in enumerate(coins):
        price_dict = prices[i] or {}

        if allow_stale and not price_dict:
            name = _get_redis_price_key(c) + ':stale'
            price_dict = price_redis.hgetall(name)

            # logger.error('{} price fallback to stale'.format(c))

        for s in sides:
            price = price_dict.get(SIDE_MAP[s])

            if price is not None:
                price = Decimal(price)

            results.append(
                Price(coin=c, price=price, side=s)
            )

    return results


PRICES_CACHE_TIMEOUT = 10


def get_external_usdt_prices(coins: list, side: str = None, allow_stale: bool = False) \
        -> Dict[str, Decimal]:

    cache_key = 'prices:ext'

    if allow_stale:
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

    prices = _fetch_redis_prices(coins, side, allow_stale=allow_stale)
    result = {r.coin: r.price for r in prices if r.price}

    if allow_stale:
        cache.set(cache_key, result, PRICES_CACHE_TIMEOUT)

    return result


def _get_price_tether_irt_nobitex():
    resp = requests.get(url="https://api.nobitex.net/v2/orderbook/USDTIRT", timeout=10)
    data = resp.json()
    status = data['status']

    if not data['asks']:
        return

    price = {'buy': data['asks'][1][0], 'sell': data['bids'][1][0]}
    data = {'price': price, 'status': status}
    return data


def _get_raw_tether_irt_price(side: str, allow_stale: bool = False) -> Decimal:
    price = price_redis.hget('price:usdtirt', SIDE_MAP[side])
    if price:
        return Decimal(price)

    try:
        data = _get_price_tether_irt_nobitex()
        if data['status'] != 'ok':
            raise TypeError
        price = Decimal(data['price'][side]) // 10

    except (requests.exceptions.ConnectionError, TimeoutError, TypeError, JSONDecodeError, KeyError):
        try:
            from ledger.utils.provider import get_provider_requester
            provider = get_provider_requester()
            price = provider.get_price('USDTIRT', side=side)

            if not price:
                if allow_stale:
                    return provider.get_price('USDTIRT', side=side, delay=DAY)
                else:
                    raise
        except:
            if allow_stale:
                price = price_redis.hget('price:usdtirt:stale', _get_redis_side(side))
                logger.error('usdt irt price fallback to stale')

                if price:
                    return Decimal(price)
                else:
                    raise
            else:
                raise

    return price


def get_external_price(coin: str, base_coin: str, side: str, allow_stale: bool = False) -> Union[Decimal, None]:
    assert side in (BUY, SELL)

    from ledger.models import Asset
    assert coin != Asset.IRT
    assert base_coin in (Asset.IRT, Asset.USDT)

    if coin == base_coin:
        return Decimal(1)

    if (coin, base_coin) == (Asset.IRT, Asset.USDT):
        return 1 / get_external_price(
            coin=Asset.USDT,
            base_coin=Asset.IRT,
            side=get_other_side(side),
            allow_stale=allow_stale
        )

    if coin != Asset.USDT:
        prices = get_external_usdt_prices([coin], side, allow_stale=allow_stale) or {}
        price_usdt = prices.get(coin)

        if price_usdt is None:
            return None

    else:
        price_usdt = 1

    base_multiplier = 1

    if base_coin == Asset.IRT:
        base_multiplier = _get_raw_tether_irt_price(side, allow_stale)

    return price_usdt * base_multiplier
