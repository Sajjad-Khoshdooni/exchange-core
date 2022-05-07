from celery import shared_task
from django.db import transaction

from accounts.models import Notification
from ledger.models import Transfer
from ledger.utils.precision import humanize_number
from ledger.withdraw.binance import handle_binance_withdraw
from ledger.withdraw.withdraw_handler import WithdrawHandler


@shared_task
def create_transaction_from_not_broadcasts():
    WithdrawHandler.create_transaction_from_not_broadcasts()


@shared_task(queue='binance')
def create_binance_withdraw(transfer_id: int):
    handle_binance_withdraw(transfer_id)


@shared_task(queue='binance')
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

        status = data['status']

        if 'txId' in data:
            transfer.trx_hash = data['txId']

        if status % 2 == 1:
            transfer.status = transfer.CANCELED
            transfer.save()
        elif status == 6:

            with transaction.atomic():
                transfer.status = transfer.DONE
                transfer.save()

                transfer.lock.release()
                transfer.build_trx()

            sent_amount = transfer.asset.get_presentation_amount(transfer.amount)
            Notification.send(
                recipient=transfer.wallet.account.user,
                title='ارسال شد: %s %s' % (humanize_number(sent_amount), transfer.wallet.asset.symbol),
                message='به ادرس %s...%s ' % (transfer.out_address[-8:], transfer.out_address[:9])
            )
