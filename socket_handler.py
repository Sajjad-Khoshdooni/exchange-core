import os

from datetime import datetime
from django.core.wsgi import get_wsgi_application

from django.conf import settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
application = get_wsgi_application()

import asyncio
import aioredis

import websockets
from websockets.exceptions import ConnectionClosed
from accounts.models.custom_token import CustomToken


DEPTH_CLIENTS = []
ORDERS_STATUS_CLIENTS = {}

async def add_client(websocket):
    is_added = False
    while True:
        try:
            subscribe_request = await websocket.recv()
            if is_added:
                continue
            if subscribe_request == 'DEPTH':
                DEPTH_CLIENTS.append(websocket)
                is_added = True
            elif subscribe_request and subscribe_request.startswith('ORDERS_STATUS'):
                user_token = subscribe_request.split(':')[1]
                token = CustomToken.objects.filter(key=user_token, type=CustomToken.WEBSOCKET).first()
                if not token:
                    break
                ORDERS_STATUS_CLIENTS[token.user.account_id] = websocket
                is_added = token.user.account_id
                market_redis.set(f'ws:market:orders:{is_added}', int(datetime.now().timestamp()))
            else:
                break
        except ConnectionClosed:
            print("Connection is Closed")
            if is_added == True:
                DEPTH_CLIENTS.remove(websocket)
            elif is_added in ORDERS_STATUS_CLIENTS:
                ORDERS_STATUS_CLIENTS.pop(is_added)
                market_redis.delete(f'ws:market:orders:{is_added}')
            is_added = False
            break


start_server = websockets.serve(add_client, 'localhost', 6789)

market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)

depth_pubsub = market_redis.pubsub()

async def broadcast_to_all():
    await depth_pubsub.psubscribe('market:depth:*')
    async for raw_message in depth_pubsub.listen():
        if not raw_message:
            continue
        if not DEPTH_CLIENTS:
            print(raw_message)
            continue
        websockets.broadcast(DEPTH_CLIENTS, raw_message['data'])

status_pubsub = market_redis.pubsub()

async def send_users_orders_status():
    await status_pubsub.psubscribe('market:orders:*')
    async for raw_message in status_pubsub.listen():
        if not raw_message:
            continue
        if not ORDERS_STATUS_CLIENTS:
            print(raw_message)
            continue
        account_id, order_id = raw_message['channel'].split(':')[-2:]
        websockets.send(ORDERS_STATUS_CLIENTS[account_id], {'order_id': order_id, 'status': raw_message['data']})


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_to_all())
loop.create_task(send_users_orders_status())
loop.run_forever()
