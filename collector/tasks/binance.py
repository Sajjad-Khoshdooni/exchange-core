from datetime import datetime, timedelta

from celery import shared_task
from django.utils import timezone

from collector.models import BinanceIncome
from provider.exchanges import BinanceFuturesHandler
import logging

logger = logging.getLogger(__name__)


DATE_PATTERN = '%Y-%m-%d %H:%M:%S.%f%z'


@shared_task()
def fill_future_binance_income(start: str = None, end: str = None):

    if end:
        end = datetime.strptime(end, DATE_PATTERN)
    else:
        end = timezone.now()
        end -= timedelta(minutes=end.minute, seconds=end.second, microseconds=end.microsecond)

    if start:
        start = datetime.strptime(start, DATE_PATTERN)
    else:
        start = end - timedelta(hours=1)

    logger.info('Fetching income in range %s and %s' % (start, end))
    incomes = BinanceFuturesHandler.get_incomes(start, end)

    if len(incomes) >= 1000:
        logger.warning('Incomes for range %s and %s reached its limit!' % (start, end))

    for income in incomes:
        BinanceIncome.objects.get_or_create(
            tran_id=income['tranId'],
            defaults={
                'symbol': income['symbol'],
                'income_type': income['incomeType'],
                'income_date': datetime.utcfromtimestamp(income['time'] // 1000),
                'income': income['income'],
                'asset': income['asset'],
            }
        )
