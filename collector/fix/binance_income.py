from datetime import timedelta

from django.utils import timezone

from collector.tasks import fill_future_binance_income


def fix_binance_income():
    s = timezone.now() - timedelta(days=60)
    for i in range(60):
        e = s + timedelta(days=1)
        fill_future_binance_income.delay(s, e)
        s += timedelta(days=1)
