import requests
from django.db import transaction

from ledger.models import Transfer
from tracker.blockchain.dtos import BlockDTO
from tracker.clients import validate_bsc_trx, validate_tron_trx


class Confirmer:
    def __init__(self, network, block_tracker):
        self.network = network
        self.block_tracker = block_tracker

    def confirm_trx(self, transfer: Transfer):
        return bool(transfer.trx_hash)

    def confirm(self, block: BlockDTO):
        pending_transfers = Transfer.objects.filter(
            block_number__lte=block.number - self.network.min_confirm,
            network=self.network,
            status=Transfer.PENDING,
        )

        for transfer in pending_transfers:

            confirmed = self.block_tracker.has(transfer.block_hash) and self.confirm_trx(transfer) and self.client_confirm(trx_hash=transfer.trx_hash)

            if confirmed:
                with transaction.atomic():
                    transfer.status = Transfer.DONE
                    transfer.build_trx()
                    transfer.save()

                transfer.alert_user()

            else:
                transfer.status = Transfer.CANCELED
                transfer.save()

    def client_confirm(self, trx_hash):
        if self.network.symbol == 'BSC':
            return validate_bsc_trx(trx_hash=trx_hash)
        elif self.network.symbol == 'TRX':
            return validate_tron_trx(trx_hash=trx_hash)
        else:
            raise NotImplementedError
