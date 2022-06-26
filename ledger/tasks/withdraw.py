from celery import shared_task

from ledger.models import Transfer
from ledger.withdraw.exchange import handle_withdraw
from ledger.utils.wallet_pipeline import WalletPipeline
from ledger.withdraw.withdraw_handler import WithdrawHandler


@shared_task
def create_transaction_from_not_broadcasts():
    WithdrawHandler.create_transaction_from_not_broadcasts()


@shared_task(queue='binance')
def create_withdraw(transfer_id: int):
    handle_withdraw(transfer_id)


@shared_task(queue='binance')
def update_binance_withdraw():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.BINANCE,
        status=Transfer.PROCESSING,
        handling=False
    )

    for transfer in re_handle_transfers:
        create_withdraw.delay(transfer.id)

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
            transfer.lock.release()
            transfer.save()
        elif status == transfer.DONE:

            with WalletPipeline() as pipeline:  # type: WalletPipeline
                transfer.status = transfer.DONE
                transfer.save()

                pipeline.release_lock(transfer.group_id)
                transfer.build_trx(pipeline)

            transfer.alert_user()
