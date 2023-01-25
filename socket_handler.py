import os

from decimal import Decimal
from django.core.wsgi import get_wsgi_application

# from django.conf import settings
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
# application = get_wsgi_application()
import json

import asyncio
import aioredis

import websockets
from websockets.exceptions import ConnectionClosed
# from accounts.models.custom_token import CustomToken


DEPTH_CLIENTS = []
ORDERS_STATUS_CLIENTS = []


async def add_client(websocket, path):
    is_added = {'DEPTH': False, 'ORDERS_STATUS': False}
    while True:
        try:
            subscribe_request = await websocket.recv()
            if any(is_added.values()):
                continue
            if subscribe_request == 'DEPTH':
                DEPTH_CLIENTS.append(websocket)
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
            for request in ('DEPTH', 'ORDERS_STATUS'):
                clients = DEPTH_CLIENTS if request == 'DEPTH' else ORDERS_STATUS_CLIENTS
                if is_added[request]:
                    clients.remove(websocket)
            break


start_server = websockets.serve(add_client, 'localhost', 6789)

# market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)
market_redis = aioredis.from_url('redis://127.0.0.1:6379/3', decode_responses=True)

depth_pubsub = market_redis.pubsub()


async def broadcast_depth():
    await depth_pubsub.psubscribe('market:depth:*')
    async for raw_message in depth_pubsub.listen():
        if not raw_message:
            continue
        if not DEPTH_CLIENTS:
            print(raw_message)
            continue
        symbol, side = raw_message['channel'].split(':')[-2:]
        price = raw_message['data']
        websockets.broadcast(DEPTH_CLIENTS, json.dumps({'symbol': symbol, 'side': side, 'price': price}))

status_pubsub = market_redis.pubsub()


async def broadcast_orders_status():
    await status_pubsub.psubscribe('market:orders:*')
    async for raw_message in status_pubsub.listen():
        if not raw_message:
            continue
        if not ORDERS_STATUS_CLIENTS:
            print(raw_message)
            continue
        symbol = raw_message['channel'].split(':')[-1]
        side, price, status = raw_message['data'].split('-')
        websockets.broadcast(ORDERS_STATUS_CLIENTS, json.dumps({'symbol': symbol, 'side': side, 'price': price, 'status': status}))


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_depth())
loop.create_task(broadcast_orders_status())
loop.run_forever()
