import logging

from celery import shared_task
from django.conf import settings
from django.db.models import Q

from ledger.models import Transfer
from ledger.withdraw.exchange import handle_provider_withdraw
from ledger.utils.wallet_pipeline import WalletPipeline
from provider.exchanges.interface.binance_interface import ExchangeHandler

logger = logging.getLogger(__name__)


@shared_task(queue='binance')
def create_provider_withdraw(transfer_id: int):
    handle_provider_withdraw(transfer_id)


@shared_task(queue='binance')
def update_provider_withdraw():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        status=Transfer.PROCESSING,
        handling=False
    ).exclude(source=Transfer.SELF)

    for transfer in re_handle_transfers:
        create_provider_withdraw.delay(transfer.id)

    transfers = Transfer.objects.filter(
        deposit=False,
        status=Transfer.PENDING
    ).exclude(source=Transfer.SELF)

    for transfer in transfers:
        data = transfer.provider_transfer.get_status()

        status = data['status']

        if 'txId' in data:
            transfer.trx_hash = data['txId']

        if status == transfer.CANCELED:
            with WalletPipeline() as pipeline:
                pipeline.release_lock(transfer.group_id)
                transfer.status = transfer.CANCELED
                transfer.save()

        elif status == transfer.DONE:

            with WalletPipeline() as pipeline:  # type: WalletPipeline
                transfer.status = transfer.DONE
                transfer.save()

                pipeline.release_lock(transfer.group_id)
                transfer.build_trx(pipeline)

            transfer.alert_user()


@shared_task(queue='blocklink')
def create_withdraw(transfer_id: int):
    if settings.DEBUG_OR_TESTING:
        return

    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.source != Transfer.SELF:
        return

    from ledger.requester.withdraw_requester import RequestWithdraw

    response = RequestWithdraw().withdraw_from_hot_wallet(
        receiver_address=transfer.out_address,
        amount=transfer.amount,
        network=transfer.network.symbol,
        asset=transfer.wallet.asset.symbol,
        transfer_id=transfer.id
    )

    resp_data = response.json()

    if response.ok:
        transfer.status = Transfer.PENDING
        transfer.trx_hash = resp_data['trx_hash']
        transfer.save(update_fields=['status', 'trx_hash'])

    elif response.status_code == 400 and resp_data.get('type') == 'NotHandled':
        transfer.source = ExchangeHandler.get_handler(transfer.asset.hedge_method).NAME
        transfer.save(update_fields=['source'])
        create_provider_withdraw(transfer_id=transfer.id)
    else:
        transfer.status = Transfer.PENDING
        transfer.save(update_fields=['status'])
        logger.warning('Error sending withdraw to blocklink', extra={
            'transfer_id': transfer_id,
            'resp': resp_data
        })


@shared_task(queue='blocklink')
def update_withdraws():

    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.SELF,
        status=Transfer.PROCESSING,
    )

    for transfer in re_handle_transfers:
        create_withdraw.delay(transfer.id)

