import json
import logging
import signal
import sys
import time
from datetime import datetime

import websocket
from django.utils import timezone

from collector.metrics import set_metric
from collector.utils.price import price_redis
from ledger.models import Asset
from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler

logger = logging.getLogger(__name__)
KUCOIN_WSS_URL = 'wss://ws-api.kucoin.com/endpoint?token='


class KucoinConsumer:
    def __init__(self, verbose: int = 0):
        self.loop = True
        self.socket = websocket.WebSocket()
        self.queue = {}
        self.last_flush_time = time.time()
        self.verbose = verbose

        logger.info('Starting kucoin Socket...')

    def get_streams(self):
        assets = list(Asset.candid_objects.filter(
            hedge_method__in=(Asset.HEDGE_KUCOIN_SPOT, Asset.HEDGE_KUCOIN_SPOT)
        ).values_list('symbol', flat=True))
        return list(map(lambda asset: KucoinSpotHandler().get_trading_symbol(asset), assets))

    def consume(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGQUIT, self.exit_gracefully)

        streams = self.get_streams()
        topic = "/market/ticker:" + ','.join(streams)

        token = KucoinSpotHandler().collect_api('/api/v1/bullet-public', method='POST')['token']
        socket_url = KUCOIN_WSS_URL + token

        self.socket.connect(socket_url, timeout=5)

        socket_id = json.loads(self.socket.recv())['id']

        self.socket.send(json.dumps({
            'id': socket_id,
            'type': "subscribe",
            "topic": topic,
            'response': True
        }))

        timestamp = int(timezone.now().timestamp())

        while self.loop:
            if self.verbose > 0:
                logger.info('Now %s' % datetime.now())

            data_str = self.socket.recv()
            data = json.loads(data_str)
            now = int(time.time())
            if now - timestamp > 45:
                timestamp = now
                self.socket.send(json.dumps({'id': socket_id, "type": "ping"}))
            self.handle_stream_data(data)



    def handle_stream_data(self, data: dict):
        if 'data' not in data:

            if self.verbose > 0:
                logger.info('ignoring %s' % data)

            return

        stream = data['data']
        symbol = data['topic'].split(':')[1]

        bid = stream['bestBid']
        ask = stream['bestAsk']

        if self.verbose > 0:
            logger.info('setting %s ask=%s, bid=%s' % (symbol, ask, bid))

        symbol = symbol.split('-')

        key = 'bin:' + symbol[0].lower() + symbol[1].lower()

        self.queue[key] = {
            'a': ask, 'b': bid
        }
        if time.time() - self.last_flush_time > 1:
            self.flush()

    def flush(self):
        flushed_count = len(self.queue)
        logger.info('%s flushing %d items' % (timezone.now().astimezone().strftime('%Y-%m-%d %H:%M:%S'), flushed_count))
        pipe = price_redis.pipeline(transaction=False)

        for (name, data) in self.queue.items():
            pipe.hset(name=name, mapping=data)
            pipe.expire(name, 30)  # todo: reduce this to 10 for volatile coins

        pipe.execute()

        self.queue = {}
        self.last_flush_time = time.time()
        set_metric('Kucoin_price_updates', value=flushed_count, incr=True)

    def exit_gracefully(self, signum, frame):
        self.loop = False

        logger.info('Closing socket...')

        self.socket.abort()
        self.socket.close()

        logger.info(f'{self.__class__.__name__} exited gracefully.')

        sys.exit()


