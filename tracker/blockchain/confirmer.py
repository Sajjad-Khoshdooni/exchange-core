from django.db import transaction

from ledger.models import Transfer
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
