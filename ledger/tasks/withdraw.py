from celery import shared_task
from django.db.models import Q

from ledger.models import Transfer
from ledger.withdraw.exchange import handle_provider_withdraw
from ledger.utils.wallet_pipeline import WalletPipeline
from ledger.withdraw.withdraw_handler import WithdrawHandler


@shared_task
def create_transaction_from_not_broadcasts():
    WithdrawHandler.create_transaction_from_not_broadcasts()


@shared_task(queue='binance')
def create_provider_withdraw(transfer_id: int):
    handle_provider_withdraw(transfer_id)


@shared_task(queue='binance')
def update_exchange_withdraw():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        status=Transfer.PROCESSING,
        handling=False
    ).filter(~Q(source=Transfer.SELF))

    for transfer in re_handle_transfers:
        create_provider_withdraw.delay(transfer.id)

    transfers = Transfer.objects.filter(
        deposit=False,
        status=Transfer.PENDING
    ).filter(~Q(source=Transfer.SELF))

    for transfer in transfers:
        data = transfer.provider_transfer.get_status()

        status = data['status']

        if 'txId' in data:
            transfer.trx_hash = data['txId']

        if status == transfer.CANCELED:
            transfer.status = transfer.CANCELED
            transfer.lock.release()
            transfer.save()
        elif status == transfer.DONE:

            with WalletPipeline() as pipeline:  # type: WalletPipeline
                transfer.status = transfer.DONE
                transfer.save()

                pipeline.release_lock(transfer.group_id)
                transfer.build_trx(pipeline)

            transfer.alert_user()
