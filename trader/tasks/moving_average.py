import logging

from celery import shared_task

from market.models import PairSymbol
from trader.bots.moving_average import MovingAverage

logger = logging.getLogger(__name__)


@shared_task(queue='trader-ma')
def update_all_moving_averages():
    for symbol in PairSymbol.objects.filter(enable=True, market_maker_enabled=True, base_asset__symbol='IRT'):
        update_moving_average.apply_async(args=(symbol.id, ), expires=5)


@shared_task(queue='trader-ma')
def update_moving_average(symbol_id: int):
    symbol = PairSymbol.objects.get(id=symbol_id)

    try:
        MovingAverage(symbol).update()
    except Exception as exp:
        logger.exception('Handling moving average failed', extra={'symbol': symbol, 'exp': exp})
