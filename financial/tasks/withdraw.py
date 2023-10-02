from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

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


@shared_task(queue='finance')
def update_withdraws():
    withdraws = FiatWithdrawRequest.objects.filter(
        status=FiatWithdrawRequest.PROCESSING,
        created__lt=timezone.now() - timedelta(seconds=FiatWithdrawRequest.FREEZE_TIME)
    ).exclude(
        withdraw_datetime__isnull=False,
        withdraw_datetime__gte=timezone.now() - timedelta(minutes=10)
    )

    for fiat_withdraw in withdraws:
        process_withdraw.delay(fiat_withdraw.id)
