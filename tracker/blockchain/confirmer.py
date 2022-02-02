from dataclasses import dataclass

from django.db import transaction

from accounts.models import Account
from ledger.models import Transfer, Trx


@dataclass
class MinimalBlockDTO:
    hash: str
    number: int


class Confirmer:
    def __init__(self, network, asset, block_tracker):
        self.asset = asset
        self.network = network
        self.block_tracker = block_tracker

    def confirm(self, block: MinimalBlockDTO):
        pending_transfers = Transfer.objects.filter(
            block_number__lte=block.number - self.network.minimum_block_to_confirm,
            status=Transfer.PENDING
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
