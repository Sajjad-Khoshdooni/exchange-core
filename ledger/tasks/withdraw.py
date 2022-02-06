from celery import shared_task

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
        deposite=False,
        source=Transfer.BINANCE,
        status=Transfer.PENDING
    )

    for transfer in transfers:
        data = transfer.provider_transfer.get_status()
        transfer.trx_hash = data['txId']
        status = data['status']

        if status % 2 == 1:
            transfer.status = transfer.CANCELED
        elif status == 6:
            transfer.status = transfer.DONE

        transfer.save()
