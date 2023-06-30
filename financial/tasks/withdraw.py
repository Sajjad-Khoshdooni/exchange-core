from celery import shared_task
from django.db import transaction

from financial.models import FiatWithdrawRequest, Gateway


@shared_task(queue='finance')
def process_withdraw(withdraw_request_id: int):
    with transaction.atomic():
        withdraw_request = FiatWithdrawRequest.objects.select_for_update().get(id=withdraw_request_id)

        if withdraw_request.status != FiatWithdrawRequest.PROCESSING:
            return

        withdraw_request.create_withdraw_request()


@shared_task(queue='finance')
def update_withdraw_status():
    to_update = FiatWithdrawRequest.objects.filter(
        status=FiatWithdrawRequest.PENDING
    ).exclude(
        gateway__type=Gateway.MANUAL
    )

    for withdraw in to_update:
        withdraw.update_status()
