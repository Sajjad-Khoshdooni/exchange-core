import logging

from django.conf import settings

from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_system_message
from ledger.models import Transfer
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger(__name__)


def handle_provider_withdraw(transfer_id: int):
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    logger.info('withdraw handling transfer_id = %d' % transfer_id)

    transfer = Transfer.objects.get(id=transfer_id)

    assert not transfer.deposit
    assert transfer.source == Transfer.PROVIDER
    assert transfer.status == transfer.PROCESSING

    resp = get_provider_requester().new_withdraw(transfer)

    if not resp.success:
        if resp.status_code == 400:
            change_to_manual(transfer)

        return

    transfer.status = transfer.PENDING
    transfer.save(update_fields=['status'])


def change_to_manual(transfer: Transfer):
    if transfer.source == Transfer.MANUAL:
        return

    transfer.source = Transfer.MANUAL
    transfer.save(update_fields=['source'])

    send_system_message("Manual withdraw", link=url_to_edit_object(transfer))
