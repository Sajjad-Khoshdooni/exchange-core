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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
application = get_wsgi_application()

# from accounts.models.custom_token import CustomToken

logger = logging.getLogger(__name__)

logging.getLogger("websockets").setLevel(logging.ERROR)


DEPTH_CLIENTS = []
ORDERS_STATUS_CLIENTS = []
TRADES_CLIENTS = []


async def add_client(websocket, path):
    is_added = {'DEPTH': False, 'ORDERS_STATUS': False, 'TRADES': False}
    while True:
        try:
            subscribe_request = await websocket.recv()
            if any(is_added.values()):
                continue
            if subscribe_request == 'DEPTH':
                DEPTH_CLIENTS.append(websocket)
            elif subscribe_request == 'TRADES':
                TRADES_CLIENTS.append(websocket)
            elif subscribe_request == 'ORDERS_STATUS':
                # user_token = subscribe_request.split(':')[1]
                # token = CustomToken.objects.filter(key=user_token, type=CustomToken.WEBSOCKET).first()
                # if not token:
                #     break
                # ORDERS_STATUS_CLIENTS[token.user.account_id] = websocket
                # is_added = token.user.account_id
                # market_redis.set(f'ws:market:orders:{is_added}', int(datetime.now().timestamp()))
                ORDERS_STATUS_CLIENTS.append(websocket)
            else:
                break
            is_added[subscribe_request] = True
        except ConnectionClosed:
            print("Connection is Closed")
            for request in ('DEPTH', 'ORDERS_STATUS', 'TRADES'):
                if request == 'DEPTH':
                    clients = DEPTH_CLIENTS
                elif request == 'TRADES':
                    clients = TRADES_CLIENTS
                elif request == 'ORDERS_STATUS':
                    clients = ORDERS_STATUS_CLIENTS
                else:
                    continue
                if is_added[request]:
                    is_added[request] = False
                    clients.remove(websocket)
            break


start_server = websockets.serve(add_client, '0.0.0.0', 6789)

market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)

depth_pubsub = market_redis.pubsub()


async def broadcast_depth():
    while True:
        try:
            await depth_pubsub.psubscribe('market:depth:*')
            async for raw_message in depth_pubsub.listen():
                if not raw_message:
                    continue
                if not DEPTH_CLIENTS:
                    print(raw_message)
                    continue
                symbol = raw_message['channel'].split(':')[-1]
                top_orders = json.loads(raw_message['data'])
                logger.info(len(DEPTH_CLIENTS))
                websockets.broadcast(DEPTH_CLIENTS, pickle.dumps({
                    'symbol': symbol,
                    'buy_price': Decimal(top_orders.get('buy_price', 'inf')),
                    'buy_amount': Decimal(top_orders.get('buy_amount', 0)),
                    'sell_price': Decimal(top_orders.get('sell_price', 0)),
                    'sell_amount': Decimal(top_orders.get('sell_amount', 0)),
                }))
        except (ConnectionError, TimeoutError) as err:
            logger.warning('redis connection error on broadcast_depth', extra={'err': err})
            logger.info('retry broadcast_depth in 10 secs')
            await asyncio.sleep(10)


trades_pubsub = market_redis.pubsub()


async def broadcast_trades():
    while True:
        try:
            await trades_pubsub.psubscribe('market:trades:*')
            async for raw_message in trades_pubsub.listen():
                if not raw_message:
                    continue
                if not TRADES_CLIENTS:
                    print(raw_message)
                    continue
                symbol = raw_message['channel'].split(':')[-1]
                if type(raw_message['data']) != str:
                    print(raw_message)
                    continue
                price, amount, maker_order_id, taker_order_id, is_buyer_maker = raw_message['data'].split('#')
                websockets.broadcast(TRADES_CLIENTS, pickle.dumps({
                    'symbol': symbol,
                    'is_buyer_maker': is_buyer_maker,
                    'price': Decimal(price),
                    'amount': Decimal(amount),
                    'maker_order_id': maker_order_id,
                    'taker_order_id': taker_order_id,
                }))
        except (ConnectionError, TimeoutError) as err:
            logger.warning('redis connection error on broadcast_trades', extra={'err': err})
            logger.info('retry broadcast_trades in 10 secs')
            await asyncio.sleep(10)


status_pubsub = market_redis.pubsub()


async def broadcast_orders_status():
    while True:
        try:
            await status_pubsub.psubscribe('market:orders:*')
            async for raw_message in status_pubsub.listen():
                if not raw_message:
                    continue
                if not ORDERS_STATUS_CLIENTS:
                    print(raw_message)
                    continue
                if type(raw_message['data']) != str:
                    print(raw_message)
                    continue
                symbol = raw_message['channel'].split(':')[-1]
                side, price, status = raw_message['data'].split('-')
                websockets.broadcast(
                    ORDERS_STATUS_CLIENTS,
                    pickle.dumps({'symbol': symbol, 'side': side, 'price': Decimal(price), 'status': status})
                )
        except (ConnectionError, TimeoutError) as err:
            logger.warning('redis connection error on broadcast_orders_status', extra={'err': err})
            logger.info('retry broadcast_orders_status in 10 secs')
            await asyncio.sleep(10)


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_depth())
loop.create_task(broadcast_orders_status())
loop.create_task(broadcast_trades())
loop.run_forever()
