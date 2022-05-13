from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from cachetools.func import ttl_cache
from django.conf import settings

from collector.price.grpc_client import gRPCClient
from collector.utils.price import price_redis
from ledger.utils.cache import cache_for
from ledger.utils.price_manager import PriceManager

BINANCE = 'binance'
NOBITEX = 'nobitex'

USDT = 'USDT'
IRT = 'IRT'

BUY, SELL = 'buy', 'sell'


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


def _fetch_prices(coins: list, side: str = None, exchange: str = BINANCE, market_symbol: str = USDT,
                  now: datetime = None) -> List[Price]:
    results = []

    if side:
        sides = [side]
    else:
        sides = [BUY, SELL]

    if exchange == BINANCE and USDT in coins:
        for s in sides:
            results.append(
                Price(coin=USDT, price=Decimal(1), side=s)
            )
        coins.remove(USDT)

    if IRT in coins:
        for s in sides:
            results.append(
                Price(coin=IRT, price=Decimal(0), side=s)
            )
        coins.remove(IRT)

    if not coins:
        return results

    if exchange == BINANCE:
        if now:
            raise NotImplemented

        pipe = price_redis.pipeline(transaction=False)
        for c in coins:
            name = 'bin:' + c.lower() + 'usdt'
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

    else:
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

        for o in orders:
            if not side:
                side = o.side

            results.append(
                Price(coin=symbol_to_coins[o.symbol], price=Decimal(o.price), side=side)
            )

    return results


def get_prices_dict(coins: list, side: str = None, exchange: str = BINANCE, market_symbol: str = USDT,
                    now: datetime = None) -> Dict[str, Decimal]:

    results = _fetch_prices(coins, side, exchange, market_symbol, now)

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
        else:
            return Decimal(0)

    prices = get_prices_dict([coin], side, exchange, market_symbol, now)

    if prices:
        return prices[coin]
    else:
        return Decimal(0)


@cache_for(time=5)
def get_tether_irt_price(side: str, now: datetime = None) -> Decimal:
    price = price_redis.hget('nob:usdtirt', SIDE_MAP[side])
    if price:
        return Decimal(price)

    tether_rial = get_price('USDT', side=side, exchange=NOBITEX, market_symbol=IRT, now=now)
    return Decimal(tether_rial / 10)


def get_trading_price_usdt(coin: str, side: str, raw_price: bool = False) -> Decimal:
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

    bid_diff = Decimal('0.005')
    ask_diff = Decimal('0.005')

    if raw_price:
        multiplier = 1
    else:
        if side == BUY:
            multiplier = 1 - bid_diff
        else:
            multiplier = 1 + ask_diff

    price = get_price(coin, side)

    return price and price * multiplier


def get_trading_price_irt(coin: str, side: str, raw_price: bool = False) -> Decimal:
    if coin == IRT:
        return Decimal(1)

    return get_trading_price_usdt(coin, side, raw_price) * get_tether_irt_price(side)
