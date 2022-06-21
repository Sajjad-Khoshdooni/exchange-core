import requests
from django.db import transaction

from ledger.models import Transfer
from tracker.blockchain.dtos import BlockDTO


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

            confirmed = self.block_tracker.has(transfer.block_hash) and self.confirm_trx(transfer)

            if confirmed:
                with transaction.atomic():
                    transfer.status = Transfer.DONE
                    transfer.build_trx()
                    transfer.save()

                transfer.alert_user()

            else:
                transfer.status = Transfer.CANCELED
                transfer.save()


class BSCConfirmer(Confirmer):
    url = 'https://api.bscscan.com/api?module=transaction&action=gettxreceiptstatus&txhash={}&apikey=H78N3ND259DJINGK7A1SNMIWDA8EUMUMFG'

    def confirm_trx(self, transfer: Transfer):
        if not super(BSCConfirmer, self).confirm_trx(transfer):
            return False

        resp = requests.get(self.url.format(transfer.trx_hash))
        return resp.json()['result']['status'] == '1'
