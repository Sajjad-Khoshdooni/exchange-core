import logging

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


@shared_task(queue='mexc')
def fetch_mexc_price(coin: str):
    symbol = MexcSpotHandler().get_trading_symbol(coin=coin)
    data = MexcSpotHandler().get_orderbook(symbol)
    queue = {}
    if not data:
        return

    bid = data['bestBid']
    ask = data['bestAsk']
    symbol = data['symbol']

    coin = symbol[:-4]

    key = 'bin:' + ExchangeHandler.rename_coin_to_big_coin(coin).lower() + 'usdt'

    coin_coefficient = ExchangeHandler.get_coin_coefficient(coin)

    queue[key] = {
        'a': decimal_to_str(Decimal(ask) * coin_coefficient), 'b': decimal_to_str(Decimal(bid) * coin_coefficient)
    }

    logger.info('%s flushing  items' % (timezone.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')))

    pipe = price_redis.pipeline(transaction=False)

    for (name, data) in queue.items():
        pipe.hset(name=name, mapping=data)
        pipe.expire(name, 30)  # todo: reduce this to 10 for volatile coins

    pipe.execute()


@shared_task(queue='mexc')
def get_mexc_coins_prices():
    coins = list(Asset.candid_objects.filter(
        hedge_method__in=(Asset.HEDGE_MEXC_SPOT, Asset.HEDGE_MEXC_FUTURES)
    ).values_list('symbol', flat=True))

    for coin in coins:
        fetch_mexc_price.delay(coin)




