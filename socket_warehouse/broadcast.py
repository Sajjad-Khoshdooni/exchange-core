import asyncio
import json
import logging
import pickle
from datetime import timedelta
from decimal import Decimal

import aioredis
import websockets
from aioredis.exceptions import ConnectionError, TimeoutError
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import F
from django.utils import timezone

from ledger.utils.external_price import BUY, SELL
from market.models import Order
from market.models.pair_symbol import PairSymbol
from socket_warehouse.client import SocketClient

logger = logging.getLogger(__name__)


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SocketBroadcast(metaclass=Singleton):
    SUBSCRIBE = 'subscribe'
    PING, PONG = 'ping', 'pong'
    ping_interval = 30
    subscribe_key = None

    DEPTH, TRADES, ORDERS_STATUS, ORDER_BOOK = 'DEPTH', 'TRADES', 'ORDERS_STATUS', 'ORDER_BOOK'

    def __init__(self):
        self.clients = {}

    @staticmethod
    async def get_broadcast_server(subscribe_request: str) -> 'SocketBroadcast':
        return BROADCAST_CLASSES_DICT.get(subscribe_request.partition(':')[0])

    async def add_new_client(self, websocket_instance, subscribe_request):
        if not self.allows_add_new_client(websocket_instance):
            return
        client_instance = SocketClient(websocket_instance, subscribe_request.partition(':')[2])
        self.clients[client_instance] = websocket_instance
        return client_instance.id

    async def get_message_client_pairs(self, message):
        return [{'message': message, 'clients': self.clients.values()}]

    async def broadcast_filtered_messages(self, message):
        message_client_pairs = await self.get_message_client_pairs(message)
        for message_client_pair in message_client_pairs:
            filtered_message = message_client_pair['message']
            clients = message_client_pair['clients']
            if clients:
                websockets.broadcast(clients, filtered_message)

    async def broadcast(self):
        raise NotImplementedError

    async def ping_clients(self):
        while True:
            await asyncio.sleep(self.ping_interval)
            if not self.clients:
                continue
            now = timezone.now()
            for client in list(filter(
                lambda c: (now - c.last_ping) > timedelta(seconds=self.ping_interval * 3), self.clients.keys()
            )):
                await self.clients[client].close()
                self.clients.pop(client, None)
            websockets.broadcast(self.clients.values(), SocketBroadcast.PING)

    async def drop_client(self, client_id):
        self.clients.pop(client_id, None)

    async def update_client_ping(self, client_id):
        if client_id in self.clients:
            self.clients[client_id].update_ping()

    def allows_add_new_client(self, websocket):
        clients_ips = list(map(lambda c: c.remote_address[0], self.clients.values()))
        remote_address = websocket.remote_address[0]
        if remote_address not in clients_ips:
            return True
        if clients_ips.count(remote_address) > 100:
            return False
        return True


class SocketUpdateBroadcast(SocketBroadcast):
    events_pubsub = None
    pubsub_pattern = None

    async def get_parsed_message(self, raw_message):
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
                    message = await self.get_parsed_message(raw_message)
                    if not message:
                        continue
                    await self.broadcast_filtered_messages(message)
            except (ConnectionError, TimeoutError) as err:
                logger.warning(f'redis connection error at {self.pubsub_pattern}', extra={'err': err})
                logger.info(f'retry {self.pubsub_pattern} in 10 secs')
                await asyncio.sleep(10)


class SocketPeriodicBroadcast(SocketBroadcast):

    def __init__(self, interval=1) -> None:
        super().__init__()
        self.interval = interval

    async def get_raw_message(self):
        raise NotImplementedError

    async def get_parsed_message(self, raw_message):
        raise NotImplementedError

    async def broadcast(self):
        while True:
            raw_message = await self.get_raw_message()
            message = await self.get_parsed_message(raw_message)
            if not message:
                continue
            await self.broadcast_filtered_messages(message)
            await asyncio.sleep(self.interval)


market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)


class OrderDepthUpdateBroadcast(SocketUpdateBroadcast):
    events_pubsub = market_redis.pubsub()
    pubsub_pattern = 'market:depth:*'
    subscribe_key = SocketBroadcast.DEPTH

    async def get_parsed_message(self, raw_message):
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

    async def get_parsed_message(self, raw_message):
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

    async def get_parsed_message(self, raw_message):
        symbol = raw_message['channel'].split(':')[-1]
        split_data = raw_message['data'].split('-')
        side, price, status = split_data[-3:]
        order_id = '-'.join(split_data[:-3])
        return pickle.dumps({
            'order_id': order_id, 'symbol': symbol, 'side': side, 'price': Decimal(price), 'status': status
        })


class OrderDepthPeriodicBroadcast(SocketPeriodicBroadcast):
    subscribe_key = SocketBroadcast.ORDER_BOOK

    @sync_to_async
    def get_raw_message(self):
        return Order.open_objects.annotate(
            unfilled_amount=F('amount') - F('filled_amount')
        ).exclude(unfilled_amount=0).order_by('symbol', 'side').values('symbol', 'side', 'price', 'unfilled_amount')

    @sync_to_async
    def get_parsed_message(self, raw_message):
        all_open_orders = raw_message
        symbols_depth_dict = {}
        symbols_id_mapping = {symbol.id: symbol for symbol in PairSymbol.objects.all()}
        for symbol_id in set(map(lambda o: o['symbol'], all_open_orders)):
            open_orders = list(filter(lambda o: o['symbol'] == symbol_id, all_open_orders))
            symbol = symbols_id_mapping[symbol_id]
            open_orders = Order.quantize_values(symbol, open_orders)
            symbol_name = symbols_id_mapping[symbol_id].name
            symbols_depth_dict[symbol_name] = {
                'symbol': symbol_name,
                'bids': Order.get_formatted_orders(open_orders, symbol, BUY),
                'asks': Order.get_formatted_orders(open_orders, symbol, SELL),
            }
        return symbols_depth_dict

    async def get_message_client_pairs(self, message):
        message_clients_pairs = []
        for symbol, depth in message.items():
            filtered_clients = dict(filter(
                lambda key_value: key_value[0].subscribe_request == symbol, self.clients.items()
            ))
            message_clients_pairs.append(
                {'message': json.dumps(depth), 'clients': filtered_clients.values()}
            )
        return message_clients_pairs


BROADCAST_CLASSES = [OrderDepthUpdateBroadcast(), TradesUpdateBroadcast(), OrdersStatusUpdateBroadcast(),
                     OrderDepthPeriodicBroadcast()]

BROADCAST_CLASSES_DICT = {instance.subscribe_key: instance for instance in BROADCAST_CLASSES}
