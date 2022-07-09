from celery import shared_task
from django.db import transaction

from ledger.models import Transfer
from stake.models import StakeRequest, StakeRevenue


@shared_task(queue='stake')
def create_stake_revenue():
    stake_requests = StakeRequest.objects.filter(status=StakeRequest.DONE)
    for stake_request in stake_requests:

        with transaction.atomic():
            StakeRevenue.objects.create(
                stake_request=stake_request,
                # group_id= ,
                # revenue= ,
            )
        Transfer

