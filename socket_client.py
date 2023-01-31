import asyncio

import websockets
from websockets.exceptions import ConnectionClosed


async def subscribe():
    async with websockets.connect('ws://localhost:6789') as websocket:
        try:
            await websocket.send('DEPTH')
        except ConnectionClosed:
            print("Connection is Closed")
            return

        while True:
            try:
                msg = await websocket.recv()
                print(type(msg))
            except ConnectionClosed:
                print("Connection is Closed")
                break


asyncio.get_event_loop().run_until_complete(subscribe())
