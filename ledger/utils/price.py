import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Union

import requests

from collector.price.grpc_client import gRPCClient
from collector.utils.price import price_redis
from ledger.utils.cache import cache_for
from ledger.utils.price_manager import PriceManager

logger = logging.getLogger(__name__)


BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'


class PriceFetchError(Exception):
    pass


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


def get_binance_price_stream(coin: str):
    from provider.exchanges import BinanceSpotHandler
    return BinanceSpotHandler().get_trading_symbol(coin).lower()


def get_tether_price_irt_grpc(side: str, now: datetime = None):
    coins = 'USDT'
    symbol_to_coins = {
        coins + IRT: coins
    }

    if not now:
        _now = datetime.now()
    else:
        _now = now

    delay = 600_000

    grpc_client = gRPCClient()
    timestamp = int(_now.timestamp() * 1000) - delay

    order_by = ('symbol', '-timestamp')
    distinct = ('symbol',)
    values = ('symbol', 'price')

    orders = grpc_client.get_current_orders(
        exchange=NOBITEX,
        symbols=tuple(symbol_to_coins.keys()),
        position=0,
        type=side,
        timestamp=timestamp,
        order_by=order_by,
        distinct=distinct,
        values=values,
    ).orders

    grpc_client.channel.close()

    return Price(coin='USDT', price=Decimal(orders[0].price), side=side).price


def get_avg_tether_price_irt_grpc(start_timestamp, end_timestamp):
    grpc_client = gRPCClient()
    response = grpc_client.get_trades_average_price_by_time(
        min_timestamp=start_timestamp,
        max_timestamp=end_timestamp,
        symbol='USDTIRT',
        exchange=NOBITEX
    ).value
    grpc_client.channel.close()
    return Decimal(response / 10)


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
        name = 'bin:' + get_binance_price_stream(c)
        pipe.hgetall(name)

    prices = pipe.execute()

    for i, c in enumerate(coins):
        price_dict = prices[i] or {}

        if allow_stale and not price_dict:
            name = 'bin:' + get_binance_price_stream(c) + ':stale'
            price_dict = price_redis.hgetall(name)

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

    if PriceManager.active():
        for r in results:
            PriceManager.set_price(r.coin, r.side, exchange, market_symbol, now, r.price)

    return {r.coin: r.price for r in results}


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


@cache_for(time=2)
def get_price_tether_irt_nobitex():
    resp = requests.get(url="https://api.nobitex.ir/v2/orderbook/USDTIRT", timeout=2)
    data = resp.json()
    status = data['status']
    price = {'buy': data['asks'][1][0], 'sell': data['bids'][1][0]}
    data = {'price': price, 'status': status}
    return data


@cache_for(time=5)
def get_tether_irt_price(side: str, now: datetime = None) -> Decimal:
    price = price_redis.hget('nob:usdtirt', SIDE_MAP[side])
    if price:
        return Decimal(price)

    try:
        data = get_price_tether_irt_nobitex()
        if data['status'] != 'ok':
            raise TypeError
        tether_rial = Decimal(data['price'][side])

    except (TimeoutError, TypeError):
        price = get_tether_price_irt_grpc(side=side, now=now)
        return Decimal(price)

    return Decimal(tether_rial / 10)


def get_trading_price_usdt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0,
                           gap: Union[Decimal, None] = None) -> Decimal:
    if coin == IRT:
        return 1 / get_tether_irt_price(get_other_side(side))

    if gap:
        spread = gap
    else:
        spread = get_spread(coin, side, value) / 100

    if raw_price:
        multiplier = 1
    else:
        if side == BUY:
            multiplier = 1 - spread
        else:
            multiplier = 1 + spread

    price = get_price(coin, side)

    return price and price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0,
                          gap: Union[Decimal, None] = None) -> Decimal:
    if coin == IRT:
        return Decimal(1)

    tether = get_tether_irt_price(side)
    price = get_trading_price_usdt(coin, side, raw_price, value=value and value / tether, gap=gap)

    if price:
        return price * tether
