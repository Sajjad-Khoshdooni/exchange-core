from celery import shared_task
from django.db import transaction

from financial.models import FiatWithdrawRequest


@shared_task(queue='transfer')
def process_withdraw(withdraw_request_id: int):
    with transaction.atomic():
        withdraw_request = FiatWithdrawRequest.objects.select_for_update().get(id=withdraw_request_id)

        if withdraw_request.status != FiatWithdrawRequest.PROCESSING:
            return

        withdraw_request.create_withdraw_request()


@shared_task(queue='finance')
def update_withdraw_status():
    withdraws = FiatWithdrawRequest.objects.filter(status=FiatWithdrawRequest.PENDING)

    for withdraw in withdraws:
        withdraw.update_status()
