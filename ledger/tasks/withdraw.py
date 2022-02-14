from celery import shared_task
from django.db import transaction

from ledger.models import Transfer
from ledger.withdraw.binance import handle_binance_withdraw
from ledger.withdraw.withdraw_handler import WithdrawHandler


@shared_task
def create_transaction_from_not_broadcasts():
    WithdrawHandler.create_transaction_from_not_broadcasts()


@shared_task()
def create_binance_withdraw(transfer_id: int):
    handle_binance_withdraw(transfer_id)


@shared_task()
def update_binance_withdraw():

    transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.BINANCE,
        status=Transfer.PENDING
    )

    for transfer in transfers:
        data = transfer.provider_transfer.get_status()
        transfer.trx_hash = data['txId']
        status = data['status']

        if status % 2 == 1:
            transfer.status = transfer.CANCELED
            transfer.save()
        elif status == 6:

            with transaction.atomic():
                transfer.status = transfer.DONE
                transfer.save()

                transfer.lock.release()
                transfer.build_trx()
