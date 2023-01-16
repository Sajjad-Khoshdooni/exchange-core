from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from financial.models import Gateway, Payment
from financial.utils.withdraw import FiatWithdraw


@shared_task(queue='finance')
def handle_missing_payments():
    # update pending payments
    now = timezone.now()

    pending_payments = Payment.objects.filter(status=Payment.PENDING, created__lte=now - timedelta(minutes=30))

    for payment in pending_payments:
        payment.payment_request.get_gateway().verify(payment)

    # update missing payments
    gateway = Gateway.get_active()
    channel = FiatWithdraw.get_withdraw_channel(gateway.type)

    channel.update_missing_payments(gateway)
