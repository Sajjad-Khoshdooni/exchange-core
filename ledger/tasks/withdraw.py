from celery import shared_task
from django.db import transaction

from ledger.models import Transfer
from ledger.withdraw.exchange import handle_withdraw
from ledger.withdraw.withdraw_handler import WithdrawHandler


@shared_task
def create_transaction_from_not_broadcasts():
    WithdrawHandler.create_transaction_from_not_broadcasts()


@shared_task(queue='interface')
def create_binance_withdraw(transfer_id: int):
    handle_withdraw(transfer_id)


@shared_task(queue='interface')
def update_binance_withdraw():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.BINANCE,
        status=Transfer.PROCESSING,
        handling=False
    )

    for transfer in re_handle_transfers:
        create_binance_withdraw.delay(transfer.id)

    transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.BINANCE,
        status=Transfer.PENDING
    )

    for transfer in transfers:
        data = transfer.provider_transfer.get_status()

        status = data.get('status')

        if 'txId' in data:
            transfer.trx_hash = data.get('txId')

        if status == transfer.CANCELED:
            transfer.status = transfer.CANCELED
            transfer.save()
        elif status == transfer.DONE:

            with transaction.atomic():
                transfer.status = transfer.DONE
                transfer.save()

                transfer.lock.release()
                transfer.build_trx()

            transfer.alert_user()
