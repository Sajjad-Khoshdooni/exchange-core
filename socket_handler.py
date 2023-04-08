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


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_depth())
loop.create_task(broadcast_orders_status())
loop.create_task(broadcast_trades())
loop.run_forever()
