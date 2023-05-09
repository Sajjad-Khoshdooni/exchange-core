import logging
import os
from time import sleep

import msgpack
from django.core.wsgi import get_wsgi_application
from django.db.models import F


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
        all_open_orders = Order.open_objects.annotate(
            unfilled_amount=F('amount') - F('filled_amount')
        ).exclude(unfilled_amount=0).order_by('symbol', 'side').values('symbol', 'side', 'price', 'unfilled_amount')
        symbols_id_mapping = {symbol.id: symbol for symbol in PairSymbol.objects.all()}
        for symbol_id in set(map(lambda o: o['symbol'], all_open_orders)):
            open_orders = list(filter(lambda o: o['symbol'] == symbol_id, all_open_orders))
            symbol = symbols_id_mapping[symbol_id]
            open_orders = Order.quantize_values(symbol, open_orders)
            symbol_name = symbols_id_mapping[symbol_id].name
            depth = {
                'symbol': symbol_name,
                'bids': Order.get_formatted_orders(open_orders, symbol, BUY),
                'asks': Order.get_formatted_orders(open_orders, symbol, SELL),
            }
            pipeline.hset('market_depth_snapshot', symbol_name, msgpack.packb(depth))
        pipeline.execute()
        sleep(1)


if __name__ == "__main__":
    main()
