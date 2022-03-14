import json
import logging
import signal
import sys
import time
from datetime import datetime

import websocket

from collector.utils.price import price_redis
from ledger.models import Asset

logger = logging.getLogger(__name__)


BINANCE_WSS_URL = 'wss://stream.binance.com:9443/stream?streams='


class BinanceConsumer:
    def __init__(self, verbose: int = 0):
        self.loop = True
        self.socket = websocket.WebSocket()
        self.queue = {}
        self.last_flush_time = time.time()
        self.verbose = verbose

        logger.info('Starting Binance Socket...')

    def get_streams(self):
        assets = list(Asset.objects.values_list('symbol', flat=True))
        return list(map(lambda asset: asset.lower() + 'usdt@depth5', assets))

    def consume(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGQUIT, self.exit_gracefully)

        streams = self.get_streams()
        socket_url = BINANCE_WSS_URL + '/'.join(streams)

        self.socket.connect(socket_url)

        self.socket.send(json.dumps({"method": "SUBSCRIBE", "params": streams,"id": 1}))

        while self.loop:
            if self.verbose > 0:
                logger.info('Now %s' % datetime.now())

            data_str = self.socket.recv()
            data = json.loads(data_str)
            self.handle_stream_data(data)

    def handle_stream_data(self, data: dict):
        if 'stream' not in data:

            if self.verbose > 0:
                logger.info('ignoring %s' % data)

            return

        stream = data['stream']
        symbol = stream.split('@')[0]

        bid = data['data']['bids'][0][0]
        ask = data['data']['asks'][0][0]

        if self.verbose > 0:
            logger.info('setting %s ask=%s, bid=%s' % (symbol, ask, bid))

        key = 'bin:' + symbol

        self.queue[key] = {
            'a': ask, 'b': bid
        }

        if time.time() - self.last_flush_time > 1:
            self.flush()

    def flush(self):
        logger.info('flushing %d items' % len(self.queue))
        pipe = price_redis.pipeline(transaction=False)

        for (name, data) in self.queue.items():
            pipe.hset(name=name, mapping=data)
            pipe.expire(name, 10)

        pipe.execute()

        self.queue = {}
        self.last_flush_time = time.time()

    def exit_gracefully(self, signum, frame):
        self.loop = False

        logger.info('Closing socket...')

        self.socket.abort()
        self.socket.close()

        logger.info(f'{self.__class__.__name__} exited gracefully.')

        sys.exit()