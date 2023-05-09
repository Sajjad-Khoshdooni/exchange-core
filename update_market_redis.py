import logging
import os
from collections import defaultdict
from time import sleep

import msgpack
from django.core.wsgi import get_wsgi_application
from django.db.models import F, Sum

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_base.settings")
application = get_wsgi_application()

from market.utils.redis import socket_server_redis
from ledger.utils.external_price import BUY, SELL
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


def main():
    logger.info('start market redis updater')
    pipeline = socket_server_redis.pipeline()
    while True:
        all_open_orders = list(Order.open_objects.values('symbol', 'side', 'price').annotate(
            unfilled_amount=Sum(F('amount') - F('filled_amount'))
        ))

        per_symbol_orders = defaultdict(list)

        for order in all_open_orders:
            per_symbol_orders[order['symbol'], order['side']].append(order)

        for symbol in PairSymbol.objects.filter(enable=True):
            bids = Order.quantize_values(symbol, per_symbol_orders.get((symbol.id, BUY)))
            asks = Order.quantize_values(symbol, per_symbol_orders.get((symbol.id, SELL)))

            depth = {
                'symbol': symbol.name,
                'bids': Order.get_formatted_orders(bids, symbol, BUY),
                'asks': Order.get_formatted_orders(asks, symbol, SELL),
            }
            pipeline.hset('market_depth_snapshot', symbol.name, msgpack.packb(depth))
        pipeline.execute()

        logger.info('market depth inserted to redis')

        sleep(1)


if __name__ == "__main__":
    main()
