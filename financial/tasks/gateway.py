from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from financial.models import Gateway, Payment
from financial.utils.payment_id_client import get_payment_id_client
from financial.utils.withdraw import FiatWithdraw


@shared_task(queue='finance')
def handle_missing_payments():
    # update pending payments
    now = timezone.now()

    pending_payments = Payment.objects.filter(status=Payment.PENDING, created__lte=now - timedelta(minutes=2))

    for payment in pending_payments:
        payment.payment_request.get_gateway().verify(payment)

    # update missing payments
    gateway = Gateway.get_active_deposit()
    channel = FiatWithdraw.get_withdraw_channel(gateway)

    channel.update_missing_payments(gateway)


@shared_task(queue='finance')
def handle_missing_payment_ids():
    gateway = Gateway.get_active_pay_id_deposit()
    client = get_payment_id_client(gateway)
    client.create_missing_payment_requests()
