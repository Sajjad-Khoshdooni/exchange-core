from django.db import transaction

from accounts.models import Notification
from ledger.models import Transfer
from ledger.utils.precision import humanize_number
from tracker.blockchain.dtos import BlockDTO


class Confirmer:
    def __init__(self, network, block_tracker):
        self.network = network
        self.block_tracker = block_tracker

    def confirm(self, block: BlockDTO):
        pending_transfers = Transfer.objects.filter(
            block_number__lte=block.number - self.network.min_confirm,
            network=self.network,
            status=Transfer.PENDING,
        )
        for transfer in pending_transfers:
            if not self.block_tracker.has(transfer.block_hash):
                transfer.status = Transfer.CANCELED
                transfer.save()
                continue

            with transaction.atomic():
                transfer.status = Transfer.DONE
                transfer.build_trx()
                transfer.save()

            received_amount = transfer.asset.get_presentation_amount(transfer.amount)
            Notification.send(
                recipient=transfer.wallet.account.user,
                title='دریافت شد: %s %s' % (transfer.wallet.asset.symbol, humanize_number(received_amount), ),
                message='از آدرس %s' % transfer.out_address
            )

