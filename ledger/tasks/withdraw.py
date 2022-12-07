import logging

from celery import shared_task
from django.conf import settings

from ledger.models import Transfer
from ledger.utils.provider import get_provider_requester
from ledger.withdraw.exchange import handle_provider_withdraw

logger = logging.getLogger(__name__)


@shared_task(queue='transfer')
def create_provider_withdraw(transfer_id: int):
    handle_provider_withdraw(transfer_id)


@shared_task(queue='transfer')
def update_provider_withdraw():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.PROVIDER,
        status=Transfer.PROCESSING,
        handling=False
    )

    for transfer in re_handle_transfers:
        create_provider_withdraw.delay(transfer.id)

    transfers = Transfer.objects.filter(
        deposit=False,
        source=Transfer.PROVIDER,
        status=Transfer.PENDING
    )

    for transfer in transfers:
        data = get_provider_requester().get_transfer_status(transfer)

        status = data.status

        if status == transfer.CANCELED:
            transfer.reject()

        elif status == transfer.DONE:
            transfer.accept(data.tx_id)


@shared_task(queue='transfer')
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

    if transfer.status != Transfer.PROCESSING:
        logger.info('ignored due to invalid status')
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


@shared_task(queue='transfer')
def update_withdraws():
    re_handle_transfers = Transfer.objects.filter(
        deposit=False,
        handling=False,
        source=Transfer.SELF,
        status=Transfer.PROCESSING,
    )

    for transfer in re_handle_transfers:
        create_withdraw.delay(transfer.id)
