import json
import logging
import signal
import sys
import time
from datetime import datetime
from decimal import Decimal

import websocket
from celery import shared_task
from django.utils import timezone

from collector.metrics import set_metric
from collector.utils.price import price_redis
from ledger.models import Asset

from ledger.utils.precision import decimal_to_str
from provider.exchanges.interface.binance_interface import ExchangeHandler
from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler
from provider.exchanges.interface.mexc_interface import MexcSpotHandler

logger = logging.getLogger(__name__)
KUCOIN_WSS_URL = 'wss://ws-api.kucoin.com/endpoint?token='


class MexcConsumer:
    def __init__(self, verbose: int = 0):
        self.loop = True
        self.socket = websocket.WebSocket()
        self.queue = {}
        self.last_flush_time = time.time()
        self.verbose = verbose

        logger.info('Starting kucoin Socket...')

    def get_streams(self):
        assets = list(Asset.candid_objects.filter(
            hedge_method__in=(Asset.HEDGE_MEXC_SPOT, Asset.HEDGE_MEXC_FUTURES)
        ).values_list('symbol', flat=True))
        return list(map(lambda asset: MexcSpotHandler().get_trading_symbol(asset), assets))

    def handle_stream_data(self, data: dict):
        if not data:

            if self.verbose > 0:
                logger.info('ignoring %s' % data)

            return

        bid = data['bestBid']
        ask = data['bestAsk']
        symbol = data['symbol']
        if self.verbose > 0:
            logger.info('setting %s ask=%s, bid=%s' % (symbol, ask, bid))

        coin = symbol[:-4]

        key = 'bin:' + ExchangeHandler.rename_coin_to_big_coin(coin).lower() + 'usdt'

        coin_coefficient = ExchangeHandler.get_coin_coefficient(coin)

        self.queue[key] = {
            'a': decimal_to_str(Decimal(ask) * coin_coefficient), 'b': decimal_to_str(Decimal(bid) * coin_coefficient)
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
        set_metric('maxc_price_updates', value=flushed_count, incr=True)

    @shared_task(queue='mexc')
    def api_consume(self):
        symbols = self.get_streams()

        logger.info('Now %s' % datetime.now())
        for symbol in symbols:
            data = MexcSpotHandler().get_orderbook(symbol)
            self.handle_stream_data(data)
        time.sleep(.1)


