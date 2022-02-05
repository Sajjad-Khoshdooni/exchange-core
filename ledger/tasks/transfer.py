import logging

from celery import shared_task

from ledger.models import Transfer
from provider.exchanges import BinanceSpotHandler
from provider.models import ProviderTransfer

logger = logging.getLogger(__name__)


@shared_task()
def handle_withdraw(transfer_id: int):
    transfer = Transfer.objects.get(id=transfer_id)

    if transfer.handling:
        logger.info('ignored because of handling flag')
        return

    try:
        transfer.handling = True
        transfer.save()

        assert not transfer.deposit
        assert transfer.source == transfer.BINANCE
        assert transfer.status == transfer.PROCESSING
        assert not transfer.provider_transfer

        balances_list = BinanceSpotHandler.get_account_details()['balances']
        balance_map = {b['asset']: b['free'] for b in balances_list}

        coin = transfer.wallet.asset.symbol
        amount = transfer.amount

        if balance_map[coin] >= amount:

    finally:
        transfer.handling = False
        transfer.save()


def withdraw(transfer: Transfer):
    ProviderTransfer.
