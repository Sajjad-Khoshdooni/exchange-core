import json
from collections import OrderedDict
from datetime import timedelta
from random import randint

from django.conf import settings
from django.utils import timezone
from redis import Redis

from ledger.utils.price import BUY

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


class MarketStreamCache:
    _client = market_redis

    SET_IF_HIGHER = 'setifhigher'
    SET_IF_LOWER = 'setiflower'
    SET_IF_NOT_EQUAL = 'setifnoteq'

    _funcs_dict = {
        SET_IF_HIGHER: "local c = tonumber(redis.call('get', KEYS[1])); if c then if tonumber(ARGV[1]) > c then redis.call('set', KEYS[1], ARGV[1]) return tonumber(ARGV[1]) - c else return 0 end else return redis.call('set', KEYS[1], ARGV[1]) end",
        SET_IF_LOWER: "local c = tonumber(redis.call('get', KEYS[1])); if c then if tonumber(ARGV[1]) < c then redis.call('set', KEYS[1], ARGV[1]) return tonumber(ARGV[1]) - c else return 0 end else return redis.call('set', KEYS[1], ARGV[1]) end",
        SET_IF_NOT_EQUAL: "local c = tonumber(redis.call('get', KEYS[1])); if c then if tonumber(ARGV[1]) ~= c then redis.call('set', KEYS[1], ARGV[1]) return tonumber(ARGV[1]) - c else return 0 end else return redis.call('set', KEYS[1], ARGV[1]) end",
    }

    def __init__(self):
        self.market_pipeline = market_redis.pipeline()

    def set_if_lower(self, k, v):
        return self._call(self.SET_IF_LOWER, **{k: v})

    def set_if_higher(self, k, v):
        return self._call(self.SET_IF_HIGHER, **{k: v})

    def set_if_not_equal(self, k, v):
        return self._call(self.SET_IF_NOT_EQUAL, **{k: v})

    def _call(self, func_name, **kwargs):
        inputs = list(sum(kwargs.items(), ()))
        return self._client.evalsha(self._load_script(func_name), int(len(inputs) / 2), *inputs)

    @classmethod
    def _load_script(cls, func_name):
        func_sha = cls._client.get(f'utils:func:{func_name}')
        if not func_sha or not cls._client.script_exists(func_sha)[0]:
            func_sha = cls._register_script(func_name)
            cls._client.set(f'utils:func:{func_name}', func_sha)
        return func_sha

    @classmethod
    def _register_script(cls, func_name):
        if func_name in cls._funcs_dict:
            return cls._client.script_load(cls._funcs_dict[func_name])
        raise NotImplementedError

    def update_bid_ask(self, symbol, side):
        from market.models import Order
        price_updated = {Order.BUY: False, Order.SELL: False}
        amount_updated = {Order.BUY: False, Order.SELL: False}
        top_orders = {}
        for order_type in (Order.BUY, Order.SELL):
            if side is None or order_type == side:
                top_order = Order.get_top_price_amount(symbol.id, order_type)
                top_orders[f'{order_type}_price'] = str(top_order.price)
                top_orders[f'{order_type}_amount'] = str(top_order.amount)
                set_func = self.set_if_higher if order_type == Order.BUY else self.set_if_lower
                price_updated[order_type] = set_func(
                    f'market:depth:price:{symbol.name}:{order_type}', str(top_order.price)
                )
                amount_updated[order_type] = self.set_if_not_equal(
                    f'market:depth:amount:{symbol.name}:{order_type}', str(top_order.amount)
                )
            else:
                top_orders[f'{order_type}_price'] = str(
                    self._client.get(f'market:depth:price:{symbol.name}:{order_type}'))
                top_orders[f'{order_type}_amount'] = str(
                    self._client.get(f'market:depth:amount:{symbol.name}:{order_type}'))

        if any(price_updated.values()) or any(amount_updated.values()):
            self.market_pipeline.publish(f'market:depth:{symbol.name}', json.dumps(top_orders))

    def update_trades(self, trade_pairs):
        if not trade_pairs:
            return
        # if not market_redis.exists(f'ws:market:orders:{account_id}'):
        #     return
        for pair in trade_pairs:
            # self.market_pipeline.publish(f'market:orders:{trade.symbol.name}:{account_id}:{order_id}', trade.order_id)
            maker_trade, taker_trade = pair
            is_buyer_maker = maker_trade.side == BUY
            self.market_pipeline.publish(
                f'market:trades:{maker_trade.symbol.name}',
                f'{maker_trade.price}#{maker_trade.amount}#{maker_trade.order_id}#{taker_trade.order_id}#{is_buyer_maker}'
            )

    def update_order_status(self, order):
        self.market_pipeline.publish(
            f'market:orders:status:{order.symbol.name}', f'{order.side}-{order.price}-{order.status}'
        )

    def execute(self, symbol, updated_orders, trade_pairs=None, side=None):
        if trade_pairs is None:
            trade_pairs = []
        for updated_order in updated_orders:
            self.update_order_status(updated_order)
        self.update_trades(trade_pairs)
        self.update_bid_ask(symbol, side)

        if self.market_pipeline:
            self.market_pipeline.execute()
