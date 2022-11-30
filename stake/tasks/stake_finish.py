from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from stake.models import StakeRequest


@shared_task(queue='celery')
def finish_stakes():
    start = timezone.now() - timedelta(days=90)

    stake_requests = StakeRequest.objects.filter(status=StakeRequest.DONE, created__lte=start)

    for stake_request in stake_requests:
        stake_request.change_status(StakeRequest.FINISHED)
