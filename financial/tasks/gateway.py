from celery import shared_task

from financial.models import Gateway
from financial.utils.withdraw import FiatWithdraw


@shared_task(queue='financial')
def handle_missing_payments():
    gateway = Gateway.get_active()
    channel = FiatWithdraw.get_withdraw_channel(gateway.type)

    channel.update_missing_payments(gateway)
