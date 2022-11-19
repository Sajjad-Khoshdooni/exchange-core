import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError
from typing import Dict, List, Union

import requests
from decouple import config
from django.conf import settings
from redis import Redis

from ledger.utils.cache import cache_for
from ledger.utils.price_manager import PriceManager

logger = logging.getLogger(__name__)

price_redis = Redis.from_url(settings.PRICE_CACHE_LOCATION, decode_responses=True)


BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'

DAY = 24 * 3600


class PriceFetchError(Exception):
    pass


def get_redis_side(side: str):
    assert side in (BUY, SELL)
    return 'a' if side == SELL else 'b'


@cache_for(300)
def get_spread(coin: str, side: str, value: Decimal = None) -> Decimal:
    from ledger.models import CategorySpread, Asset

    asset = Asset.get(coin)
    step = CategorySpread.get_step(value)

    category = asset.spread_category

    spread = CategorySpread.objects.filter(category=category, step=step, side=side).first()

    if not spread:
        logger.warning("No category spread defined for %s step = %s, side = %s" % (category, step, side))
        spread = CategorySpread()

    return spread.spread


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


BUSD_COINS = ('HNT', )


def get_redis_price_key(coin: str):
    if coin in BUSD_COINS:
        base = 'busd'
    else:
        base = 'usdt'

    return 'price:' + coin.lower() + base


def _fetch_prices(coins: list, side: str = None, exchange: str = BINANCE,
                  now: datetime = None, allow_stale: bool = False) -> List[Price]:
    results = []

    if side:
        sides = [side]
    else:
        sides = [BUY, SELL]

    assert exchange == BINANCE

    if USDT in coins:  # todo: check if market_symbol = USDT
        for s in sides:
            results.append(
                Price(coin=USDT, price=Decimal(1), side=s)
            )
        coins.remove(USDT)

    if 'USDC' in coins:
        for s in sides:
            results.append(
                Price(coin='USDC', price=Decimal(1), side=s)
            )
        coins.remove('USDC')

    if 'TUSD' in coins:
        for s in sides:
            results.append(
                Price(coin='TUSD', price=Decimal(1), side=s)
            )
        coins.remove('TUSD')

    if IRT in coins:  # todo: check if market_symbol = IRT
        for s in sides:
            results.append(
                Price(coin=IRT, price=Decimal(0), side=s)
            )
        coins.remove(IRT)

    if not coins:
        return results

    if now:
        raise NotImplemented

    pipe = price_redis.pipeline(transaction=False)
    for c in coins:
        name = get_redis_price_key(c)
        pipe.hgetall(name)

    prices = pipe.execute()

    for i, c in enumerate(coins):
        price_dict = prices[i] or {}

        if allow_stale and not price_dict:
            name = get_redis_price_key(c) + ':stale'
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


def get_prices_dict(coins: list, side: str = None, exchange: str = BINANCE, market_symbol: str = USDT,
                    now: datetime = None, allow_stale: bool = False) -> Dict[str, Decimal]:
    results = _fetch_prices(coins, side, exchange, now, allow_stale=allow_stale)

    return {r.coin: r.price for r in results}


def get_price(coin: str, side: str, exchange: str = BINANCE, market_symbol: str = USDT,
              now: datetime = None, allow_stale: bool = False) -> Decimal:
    if PriceManager.active():
        price = PriceManager.get_price(coin, side)
        if price is not None:
            return price

    prices = get_prices_dict([coin], side, exchange, market_symbol, now, allow_stale=allow_stale)

    if prices:
        return prices[coin]
    else:
        return Decimal(0)


def get_price_tether_irt_nobitex():
    resp = requests.get(url="https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=10)
    data = resp.json()
    status = data['status']

    if not data['asks']:
        return

    price = {'buy': data['asks'][1][0], 'sell': data['bids'][1][0]}
    data = {'price': price, 'status': status}
    return data


def get_tether_irt_price(side: str, allow_stale: bool = False) -> Decimal:
    if PriceManager.active():
        price = PriceManager.get_tether_price(side)
        if price is not None:
            return price

    price = price_redis.hget('price:usdtirt', SIDE_MAP[side])
    if price:
        return Decimal(price)

    try:
        data = get_price_tether_irt_nobitex()
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
                price = price_redis.hget('price:usdtirt:stale', get_redis_side(side))
                logger.error('usdt irt price fallback to stale')

                if price:
                    return Decimal(price)
                else:
                    raise
            else:
                raise

    return price


def get_trading_price_usdt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0,
                           gap: Union[Decimal, None] = None, allow_stale: bool = False) -> Decimal:
    if coin == IRT:
        return 1 / get_tether_irt_price(get_other_side(side), allow_stale=allow_stale)

    if gap:
        spread = gap
    else:
        spread = get_spread(coin, side, value) / 100

    if config('AUTO_SPREAD_SHEER', cast=bool, default=False):
        spread_sheer = Decimal('0.5')
    else:
        spread_sheer = 0

    if raw_price:
        multiplier = 1
    else:
        if side == BUY:

            multiplier = 1 - spread * (1 - spread_sheer)
        else:
            multiplier = 1 + spread * (1 + spread_sheer)

    price = get_price(coin, side, allow_stale=allow_stale)

    return price and price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0,
                          gap: Union[Decimal, None] = None, allow_stale: bool = False) -> Decimal:
    """

    :rtype: object
    """
    if coin == IRT:
        return Decimal(1)

    tether = get_tether_irt_price(side)
    price = get_trading_price_usdt(coin, side, raw_price, value=value and value / tether, gap=gap,
                                   allow_stale=allow_stale)

    if price:
        return price * tether
