import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from ledger.models import OTCTrade


logger = logging.getLogger(__name__)


@shared_task(queue='celery')
def accept_pending_otc_trades():
    expire = timezone.now() - timedelta(seconds=60)

    for otc in OTCTrade.objects.filter(status=OTCTrade.PENDING, created__lt=expire):
        try:
            otc.hedge_with_provider()
        except Exception as e:
            logger.exception('failed to hedge otc', extra={'exp': e})
