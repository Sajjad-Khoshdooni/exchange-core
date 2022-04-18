from celery import shared_task

from market.models import PairSymbol
from trader.bots.moving_average import MovingAverage


@shared_task(queue='trader-ma')
def update_all_moving_averages():
    for symbol in PairSymbol.objects.filter(enable=True, market_maker_enabled=True):
        update_moving_average.apply_async(args=(symbol.id, ), expires=5)


@shared_task(queue='trader-ma')
def update_moving_average(symbol_id: int):
    symbol = PairSymbol.objects.get(id=symbol_id)

    MovingAverage(symbol).update()
