import asyncio
import json
import logging
import os
import pickle
from decimal import Decimal

import aioredis
import websockets
from aioredis.exceptions import ConnectionError, TimeoutError
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from websockets.exceptions import ConnectionClosed
from ledger.utils.external_price import BUY, SELL
from market.models import Order
from django.db.models import F

from market.models.pair_symbol import PairSymbol

logger = logging.getLogger(__name__)

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class SocketBroadcast(metaclass=Singleton):
    SUBSCRIBE_KEY = None
    clients = []

    DEPTH, TRADES, ORDERS_STATUS, ORDER_BOOK = 'DEPTH', 'TRADES', 'ORDERS_STATUS', 'ORDER_BOOK'

    def get_message_client_pairs(self, message):
        return [{'message': message, 'clients': self.clients}]

    def broadcast_filtered_messages(self, message):
        message_client_pairs = self.get_message_client_pairs(message)
        for message_client_pair in message_client_pairs:
            filtered_message = message_client_pair['message']
            clients = message_client_pair['clients']
            websockets.broadcast(clients, filtered_message)

    async def broadcast(self):
        raise NotImplementedError
    

class SocketUpdateBroadcast(SocketBroadcast):
    events_pubsub = None
    pubsub_pattern = None

    def get_parsed_message(self, raw_message):
        raise NotImplementedError

    async def broadcast(self):
        if not self.events_pubsub:
            raise Exception('events_pubsub is missing')
        while True:
            try:
                await self.events_pubsub.psubscribe(self.pubsub_pattern)
                async for raw_message in self.events_pubsub.listen():
                    if not raw_message:
                        continue
                    if not self.clients:
                        print(raw_message)
                        continue
                    if type(raw_message['data']) != str:
                        print(raw_message)
                        continue
                    message = self.get_parsed_message(raw_message)
                    if not message:
                        continue
                    self.broadcast_filtered_messages(message)
            except (ConnectionError, TimeoutError) as err:
                logger.warning(f'redis connection error at {self.pubsub_pattern}', extra={'err': err})
                logger.info(f'retry {self.pubsub_pattern} in 10 secs')
                await asyncio.sleep(10)
    


class SocketPeriodicBroadcast(SocketBroadcast):

    def __init__(self, interval=1) -> None:
        super().__init__()
        self.interval = interval

    def get_raw_message(self):
        raise NotImplementedError

    def get_parsed_message(self, raw_message):
        raise NotImplementedError

    async def broadcast(self):
        while True:
            raw_message = self.get_raw_message()
            message = self.get_parsed_message(raw_message)
            if not message:
                continue
            self.broadcast_filtered_messages(message)
            await asyncio.sleep(self.interval)
    
market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)

class OrderDepthUpdateBroadcast(SocketUpdateBroadcast):
    events_pubsub = market_redis.pubsub()
    pubsub_pattern = 'market:depth:*'
    subscribe_key = SocketBroadcast.DEPTH

    def get_parsed_message(self, raw_message):
        symbol = raw_message['channel'].split(':')[-1]
        try:
            top_orders = json.loads(raw_message['data'])
        except TypeError:
            return
        return pickle.dumps({
            'symbol': symbol,
            'buy_price': Decimal(top_orders.get('buy_price', 0)),
            'buy_amount': Decimal(top_orders.get('buy_amount', 0)),
            'sell_price': Decimal(top_orders.get('sell_price', 'inf')),
            'sell_amount': Decimal(top_orders.get('sell_amount', 0)),
        })


class TradesUpdateBroadcast(SocketUpdateBroadcast):
    events_pubsub = market_redis.pubsub()
    pubsub_pattern = 'market:trades:*'
    subscribe_key = SocketBroadcast.TRADES


    def get_parsed_message(self, raw_message):
        symbol = raw_message['channel'].split(':')[-1]
        origin_id, price, amount, maker_order_id, taker_order_id, is_buyer_maker = raw_message['data'].split('#')
        return pickle.dumps({
            'symbol': symbol,
            'is_buyer_maker': is_buyer_maker,
            'price': Decimal(price),
            'amount': Decimal(amount),
            'maker_order_id': maker_order_id,
            'taker_order_id': taker_order_id,
            'origin_id': origin_id
        })

class OrdersStatusUpdateBroadcast(SocketUpdateBroadcast):
    events_pubsub = market_redis.pubsub()
    pubsub_pattern = 'market:orders:*'
    subscribe_key = SocketBroadcast.ORDERS_STATUS

    def get_parsed_message(self, raw_message):
        symbol = raw_message['channel'].split(':')[-1]
        split_data = raw_message['data'].split('-')
        side, price, status = split_data[-3:]
        order_id = '-'.join(split_data[:-3])
        return pickle.dumps({
            'order_id': order_id, 'symbol': symbol, 'side': side, 'price': Decimal(price), 'status': status
        })

class OrderDepthPeriodicBroadcast(SocketPeriodicBroadcast):
    subscribe_key = SocketBroadcast.ORDER_BOOK

    def get_raw_message(self):
        return Order.open_objects.annotate(
            unfilled_amount=F('amount') - F('filled_amount')
        ).exclude(unfilled_amount=0).order_by('symbol', 'side').values('symbol', 'side', 'price', 'unfilled_amount')

    def get_parsed_message(self, raw_message):
        all_open_orders = raw_message
        symbols_depth_dict = {}
        symbols_id_mapping = {symbol.id: symbol for symbol in PairSymbol.objects.all()}
        for symbol_id in set(map(lambda o: o['symbol'], all_open_orders)):
            open_orders = list(filter(lambda o: o['symbol'] == symbol_id, open_orders))
            symbol = symbols_id_mapping[symbol_id]
            open_orders = Order.quantize_values(symbol, open_orders)
            symbol_name = symbols_id_mapping[symbol_id].name
            symbols_depth_dict[symbol_name] = {
                'symbol': symbol_name,
                'bids': Order.get_formatted_orders(open_orders, symbol, BUY),
                'asks': Order.get_formatted_orders(open_orders, symbol, SELL),
            }
        return symbols_depth_dict

    def get_message_client_pairs(self, message):
        message_clients_pairs = []
        for symbol, depth in message.items():
            message_clients_pairs.append(
                {'message': depth, 'clients': list(filter(lambda c: c.symbol == symbol, self.clients))}
            )
        return message_clients_pairs
