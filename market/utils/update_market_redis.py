import logging
from time import sleep

import msgpack
from django.db.models import F

from ledger.utils.external_price import BUY, SELL
from market.models import Order, PairSymbol
from market.utils.redis import socket_server_redis

logger = logging.getLogger(__name__)


def run():
    logger.info('start market redis updater')

    pipeline = socket_server_redis.pipeline()
    while True:
        open_orders = Order.open_objects.annotate(
            unfilled_amount=F('amount') - F('filled_amount')
        ).exclude(unfilled_amount=0).order_by('symbol', 'side').values('symbol', 'side', 'price', 'unfilled_amount')
        symbols_id_mapping = {symbol.id: symbol for symbol in PairSymbol.objects.all()}
        for symbol_id in set(map(lambda o: o['symbol'], open_orders)):
            open_orders = list(filter(lambda o: o['symbol'] == symbol_id, open_orders))
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
    run()
