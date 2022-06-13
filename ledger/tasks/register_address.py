from celery import shared_task

from ledger.models.deposit_address import DepositAddress
from ledger.requester.register_address_requester import RegisterAddress


@shared_task()
def register_address():
    deposits = DepositAddress.objects.filter(is_registered=False)

    for deposit in deposits:
        RegisterAddress().register(address=deposit.address, network=deposit.network)
