import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
from django.conf import settings

import asyncio
import aioredis

import websockets
from websockets.exceptions import ConnectionClosed

CLIENTS = []


async def add_client(websocket):
    is_added = False
    while True:
        try:
            data = await websocket.recv()
            print(data)
            if is_added:
                continue
            CLIENTS.append(websocket)
        except ConnectionClosed:
            print("Connection is Closed")
            CLIENTS.remove(websocket)
            data = None
            break


start_server = websockets.serve(add_client, 'localhost', 6789)

market_redis = aioredis.from_url(settings.MARKET_CACHE_LOCATION, decode_responses=True)

pubsub = market_redis.pubsub()


async def broadcast_to_all():
    await pubsub.psubscribe('market:depth:*')
    async for raw_message in pubsub.listen():
        if not raw_message:
            continue
        if not CLIENTS:
            print(raw_message)
            continue
        websockets.broadcast(CLIENTS, raw_message['data'])


loop = asyncio.get_event_loop()
loop.run_until_complete(start_server)
loop.create_task(broadcast_to_all())
loop.run_forever()
