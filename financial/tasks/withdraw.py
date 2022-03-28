from financial.models import FiatWithdrawRequest
from ledger.utils.fields import PENDING
from celery import shared_task


@shared_task(queue='celery')
def withdraw_update_provider_request_status():
    withdraws = FiatWithdrawRequest.objects.filter(provider_request_status=PENDING)

    for withdraw in withdraws:
        withdraw.update_providing_status()
