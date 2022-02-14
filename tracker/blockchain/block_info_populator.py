from ledger.models import Transfer
from tronpy import Tron
from tronpy.exceptions import TransactionNotFound


class BlockInfoPopulator:
    pass


class TRXBlockInfoPopulator(BlockInfoPopulator):
    symbol = 'TRX'

    def __init__(self, tron_client: Tron):
        self.tron = tron_client

    def populate(self):
        to_populate_transfers = Transfer.objects.filter(network__symbol=self.symbol, block_hash='').exclude(trx_hash='')

        for transfer in to_populate_transfers:
            try:
                transaction_info = self.tron.get_solid_transaction_info(transfer.trx_hash)
            except TransactionNotFound:
                continue
            block_number = transaction_info['blockNumber']
            block = self.tron.get_block(block_number)
            transfer.block_number = block_number
            transfer.block_hash = block['blockID']
            transfer.save()
