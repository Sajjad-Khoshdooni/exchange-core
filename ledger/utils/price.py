from _testcapi import raise_exception
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

import requests
from cachetools.func import ttl_cache

from collector.price.grpc_client import gRPCClient
from collector.utils.price import price_redis
from ledger.utils.cache import cache_for
from ledger.utils.price_manager import PriceManager
from provider.exchanges import BinanceSpotHandler

BINANCE = 'binance'
NOBITEX = 'nobitex'
KUCOIN = 'kucoin'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'

ASSET_DIFF_MULTIPLIER = {
    'LUNC': 6,
    'LUNA': 10,
    'OP': 10,
}


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
    return BinanceSpotHandler().get_trading_symbol(coin).lower()


def get_asset_diff_multiplier(coin: str):
    return ASSET_DIFF_MULTIPLIER.get(coin, 1)


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


def _fetch_prices(coins: list, side: str = None, exchange: str = BINANCE,
                  now: datetime = None) -> List[Price]:
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

        for s in sides:
            price = price_dict.get(SIDE_MAP[s])
            if price is not None:
                price = Decimal(price)

            results.append(
                Price(coin=c, price=price, side=s)
            )

    return results


def get_prices_dict(coins: list, side: str = None, exchange: str = BINANCE, market_symbol: str = USDT,
                    now: datetime = None) -> Dict[str, Decimal]:
    results = _fetch_prices(coins, side, exchange, now)

    if PriceManager.active():
        for r in results:
            PriceManager.set_price(r.coin, r.side, exchange, market_symbol, now, r.price)

    return {r.coin: r.price for r in results}


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
        return price

    return Decimal(tether_rial / 10)


def get_trading_price_usdt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0) -> Decimal:
    # from ledger.models.asset import Asset

    if coin == IRT:
        return 1 / get_tether_irt_price(get_other_side(side))

    # note: commented to decrease performance issues
    # asset = Asset.get(coin)
    #
    # bid_diff = asset.bid_diff
    # if bid_diff is None:
    #     bid_diff = Decimal('0.005')
    #
    # ask_diff = asset.ask_diff
    # if ask_diff is None:
    #     ask_diff = Decimal('0.005')

    bid_diff = Decimal('0.005') * get_asset_diff_multiplier(coin)
    ask_diff = Decimal('0.005') * get_asset_diff_multiplier(coin)

    diff_multiplier = 1

    if value:
        if value > 1000:
            diff_multiplier = 4
        elif value > 10:
            diff_multiplier = 2

    if raw_price:
        multiplier = 1
    else:
        if side == BUY:
            multiplier = 1 - bid_diff * diff_multiplier
        else:
            multiplier = 1 + ask_diff * diff_multiplier

    price = get_price(coin, side)

    return price and price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False, value: Decimal = 0) -> Decimal:
    if coin == IRT:
        return Decimal(1)

    tether = get_tether_irt_price(side)
    price = get_trading_price_usdt(coin, side, raw_price, value=value and value / tether)

    if price:
        return price * tether
