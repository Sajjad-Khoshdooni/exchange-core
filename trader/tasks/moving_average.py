from celery import shared_task

from trader.models.moving_average import MovingAverage


@shared_task()
def check_moving_average():
    for ma in MovingAverage.objects.filter(enable=True, symbol__enable=True, symbol__market_maker_enabled=True):
        ma.update()
