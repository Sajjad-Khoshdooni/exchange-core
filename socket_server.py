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

from socket_warehouse.broadcast import SocketBroadcast, BROADCAST_CLASSES

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
application = get_wsgi_application()

# from accounts.models.custom_token import CustomToken

logger = logging.getLogger(__name__)

logging.getLogger("websockets").setLevel(logging.ERROR)


async def add_client(websocket, path):
    request, client_id = None, None
    while True:
        try:
            request = await websocket.recv()
            request_type, _, request_msg = request.partition(':')
            broadcast_server = await SocketBroadcast.get_broadcast_server(request_msg)
            if not broadcast_server:
                print(request_msg)
                continue
            if request_type == SocketBroadcast.SUBSCRIBE:
                client_id = await broadcast_server.add_new_client(websocket, request_msg)
            elif request_type == SocketBroadcast.PING:
                await broadcast_server.update_client_ping(request_msg)
            else:
                continue
        except ConnectionClosed:
            print(f"Connection is Closed {client_id} {request}")
            if not request:
                break
            if not client_id:
                break
            broadcast_server = await SocketBroadcast.get_broadcast_server(request)
            if broadcast_server:
                await broadcast_server.drop_client(client_id)
            break


start_server = websockets.serve(add_client, '0.0.0.0', 6789)


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
for server in BROADCAST_CLASSES:
    loop.create_task(server.broadcast())
loop.run_forever()
