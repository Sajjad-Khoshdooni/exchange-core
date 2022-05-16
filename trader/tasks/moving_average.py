import logging
import random

from celery import shared_task

from market.models import PairSymbol
from trader.bots.moving_average import MovingAverage
from trader.bots.utils import balance_tether

logger = logging.getLogger(__name__)


@shared_task(queue='trader-ma')
def update_all_moving_averages():
    if random.randint(0, 60) == 0:  # balance every one hour
        balance_tether(MovingAverage.get_account())

    for symbol in PairSymbol.objects.filter(enable=True, market_maker_enabled=True):
        update_moving_average.apply_async(args=(symbol.id, ), expires=5)


@shared_task(queue='trader-ma')
def update_moving_average(symbol_id: int):
    symbol = PairSymbol.objects.get(id=symbol_id)

    try:
        MovingAverage(symbol).update()
    except Exception as exp:
        logger.exception('Handling moving average failed', extra={'symbol': symbol, 'exp': exp})
