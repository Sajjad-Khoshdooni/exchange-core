from financial.models import FiatWithdrawRequest
from celery import shared_task


@shared_task(queue='finance')
def process_withdraw(withdraw_request_id: int):
    withdraw_request = FiatWithdrawRequest.objects.get(id=withdraw_request_id)

    if withdraw_request.status != FiatWithdrawRequest.PROCESSING:
        return

    withdraw_request.create_withdraw_request_paydotir()


@shared_task(queue='finance')
def update_withdraw_status():
    withdraws = FiatWithdrawRequest.objects.filter(status=FiatWithdrawRequest.PENDING)

    for withdraw in withdraws:
        withdraw.update_status()
