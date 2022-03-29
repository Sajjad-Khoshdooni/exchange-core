from financial.models import FiatWithdrawRequest
from ledger.utils.fields import PENDING
from celery import shared_task


@shared_task(queue='celery')
def withdraw_update_provider_request_status():
    withdraws = FiatWithdrawRequest.objects.filter(provider_request_status=PENDING)

    for withdraw in withdraws:
        withdraw.update_providing_status()


@shared_task(queue='celery')
def create_withdraw_request_paydotir_task(withdraw_request_id: int):

    withdraw_request = FiatWithdrawRequest.objects.get(id=withdraw_request_id)
    withdraw_request.create_withdraw_request_paydotir()
