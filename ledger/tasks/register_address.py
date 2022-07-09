from celery import shared_task

from ledger.models.deposit_address import DepositAddress
from ledger.requester.register_address_requester import RegisterAddress


@shared_task()
def register_address():
    non_registered_deposits = DepositAddress.objects.filter(is_registered=False)

    deposit_register = RegisterAddress()
    for deposit in non_registered_deposits:
        deposit_register.register(deposit_address=deposit)
