import os
import pickle

from decimal import Decimal
from django.core.wsgi import get_wsgi_application

from django.conf import settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
application = get_wsgi_application()

import asyncio
import aioredis

import websockets
from websockets.exceptions import ConnectionClosed
# from accounts.models.custom_token import CustomToken


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
                    clients.remove(websocket)
            break


start_server = websockets.serve(add_client, '0.0.0.0', 6789)

market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)

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
        price = Decimal(raw_message['data'])
        websockets.broadcast(DEPTH_CLIENTS, pickle.dumps({'symbol': symbol, 'side': side, 'price': price}))


trades_pubsub = market_redis.pubsub()


async def broadcast_trades():
    await trades_pubsub.psubscribe('market:trades:*')
    async for raw_message in trades_pubsub.listen():
        if not raw_message:
            continue
        if not TRADES_CLIENTS:
            print(raw_message)
            continue
        symbol, side = raw_message['channel'].split(':')[-2:]
        price, amount, order_id, group_id = raw_message['data'].split('#')
        websockets.broadcast(TRADES_CLIENTS, pickle.dumps({
            'symbol': symbol,
            'side': side,
            'price': Decimal(price),
            'amount': Decimal(amount),
            'order_id': order_id,
            'group_id': group_id,
        }))

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
        websockets.broadcast(ORDERS_STATUS_CLIENTS,
                             pickle.dumps({'symbol': symbol, 'side': side, 'price': Decimal(price), 'status': status}))


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_depth())
loop.create_task(broadcast_orders_status())
loop.run_forever()
