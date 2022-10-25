import logging

from celery import shared_task
from django.conf import settings

from ledger.models import Transfer
from ledger.utils.provider import get_provider_requester
from ledger.utils.wallet_pipeline import WalletPipeline
from ledger.withdraw.exchange import handle_provider_withdraw

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
        data = get_provider_requester().get_transfer_status(transfer.id)

        status = data.status

        if 'txId' in data:
            transfer.trx_hash = data.tx_id

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
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    if transfer.source != Transfer.SELF:
        logger.info('ignored because non self source')
        return

    from ledger.requester.withdraw_requester import RequestWithdraw

    try:
        transfer.handling = True
        transfer.save(update_fields=['handling'])

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
            transfer.save(update_fields=['status'])

        elif response.status_code == 400 and resp_data.get('type') == 'NotHandled':
            logger.info('withdraw switch %s %s' % (transfer.id, resp_data))

            transfer.source = Transfer.PROVIDER
            transfer.save(update_fields=['source'])
            create_provider_withdraw(transfer_id=transfer.id)
        else:
            logger.info('withdraw failed %s %s %s' % (transfer.id, response.status_code, resp_data))

            transfer.status = Transfer.PENDING
            transfer.save(update_fields=['status'])

            logger.warning('Error sending withdraw to blocklink', extra={
                'transfer_id': transfer_id,
                'resp': resp_data
            })

    finally:
        transfer.handling = False
        transfer.save(update_fields=['handling'])


@shared_task(queue='blocklink')
def update_withdraws():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        handling=False,
        source=Transfer.SELF,
        status=Transfer.PROCESSING,
    )

    for transfer in re_handle_transfers:
        create_withdraw.delay(transfer.id)
