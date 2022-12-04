import logging
import time
from decimal import Decimal

from django.conf import settings

from ledger.models import Transfer, Asset
from ledger.utils.price import BUY, get_price, SELL
from ledger.utils.provider import get_provider_requester, BINANCE

logger = logging.getLogger(__name__)


def handle_provider_withdraw(transfer_id: int):
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    logger.info('withdraw handling transfer_id = %d' % transfer_id)

    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    try:
        transfer.handling = True
        transfer.save(update_fields=['handling'])

        assert not transfer.deposit
        assert transfer.source == Transfer.PROVIDER
        assert transfer.status == transfer.PROCESSING

        success = get_provider_requester().new_withdraw(transfer)

        if not success:
            return

        transfer.status = transfer.PENDING
        transfer.save(update_fields=['status'])

    finally:
        transfer.handling = False
        transfer.save(update_fields=['handling'])
