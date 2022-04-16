from celery import shared_task

from trader.models.moving_average import MovingAverage


@shared_task()
def check_moving_average():
    for ma in MovingAverage.objects.filter(enable=True):
        ma.update()
