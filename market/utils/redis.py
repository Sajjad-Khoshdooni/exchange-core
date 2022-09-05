from datetime import timedelta
from random import randint

from django.conf import settings
from django.utils import timezone
from redis import Redis

prefix_top_price = 'market_top_price'
prefix_top_depth_price = 'market_top_depth_price'
prefix_orders_count = 'market_orders_count'
prefix_order_size_factor = 'market_order_size_factor'

market_redis = Redis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)


def set_top_prices(symbol_id, price_dict, scope=''):
    set_dict_values(symbol_id, f'{prefix_top_price}:{scope}', price_dict)


def get_top_prices(symbol_id, scope=''):
    return get_as_dict(symbol_id, f'{prefix_top_price}:{scope}')


def set_top_depth_prices(symbol_id, price_dict):
    set_dict_values(symbol_id, prefix_top_depth_price, price_dict)


def get_top_depth_prices(symbol_id):
    return get_as_dict(symbol_id, prefix_top_depth_price)


def set_open_orders_count(symbol_id, orders_count):
    set_dict_values(symbol_id, prefix_orders_count, orders_count)


def get_open_orders_count(symbol_id):
    return get_as_dict(symbol_id, prefix_orders_count)


def get_daily_order_size_factors(symbol_ids):
    if market_redis.exists(prefix_order_size_factor):
        symbol_factors = market_redis.hgetall(prefix_order_size_factor)

        absent_symbols = list(filter(lambda s: str(s) not in symbol_factors.keys(), symbol_ids))
        for symbol_id in absent_symbols:
            symbol_factors[symbol_id] = randint(1, 10)
            market_redis.hset(prefix_order_size_factor, symbol_id, symbol_factors[symbol_id])
        return {int(k): int(v) for k, v in symbol_factors.items()}

    symbol_factors = {}
    pipeline = market_redis.pipeline()
    for symbol_id in symbol_ids:
        symbol_factors[symbol_id] = randint(1, 10)
        pipeline.hset(prefix_order_size_factor, symbol_id, symbol_factors[symbol_id])

    tomorrow = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    pipeline.expireat(prefix_order_size_factor, int(tomorrow.timestamp()))
    pipeline.execute()
    return symbol_factors


def set_dict_values(symbol_id, key, data):
    for side, value in data.items():
        market_redis.hset(key, f'{symbol_id}:{side}', str(value))
    market_redis.expire(key, 2)


def get_as_dict(symbol_id, key):
    as_dict = {side: market_redis.hget(key, f'{symbol_id}:{side}') for side in ('buy', 'sell')}
    if None in as_dict.values():
        return
    return as_dict
