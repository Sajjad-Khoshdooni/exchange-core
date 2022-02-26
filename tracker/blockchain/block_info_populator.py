from abc import ABC, abstractmethod
from typing import List

from tronpy import Tron
from tronpy.exceptions import TransactionNotFound as TronTransactionNotFound
from web3 import Web3
from web3.exceptions import TransactionNotFound as Web3TransactionNotFound

from _helpers.blockchain.bsc import get_web3_bsc_client
from _helpers.blockchain.eth import get_web3_eth_client
from _helpers.blockchain.tron import get_tron_client
from ledger.models import Transfer, Network


class BlockInfoPopulator(ABC):
    @abstractmethod
    def populate(self):
        pass


class TRXBlockInfoPopulator(BlockInfoPopulator):
    symbol = 'TRX'

    def __init__(self, tron_client: Tron):
        self.tron = tron_client

    def populate(self):
        to_populate_transfers = Transfer.objects.filter(
            network__symbol=self.symbol,
            block_hash='',
            source=Transfer.SELF
        ).exclude(trx_hash=None)

        for transfer in to_populate_transfers:
            try:
                transaction_info = self.tron.get_solid_transaction_info(transfer.trx_hash)
            except TronTransactionNotFound:
                continue
            block_number = transaction_info['blockNumber']
            block = self.tron.get_block(block_number)
            transfer.block_number = block_number
            transfer.block_hash = block['blockID']
            transfer.save()


class Web3BlockInfoPopulator(BlockInfoPopulator):
    def __init__(self, web3_client: Web3, network: Network):
        self.web3 = web3_client
        self.network = network

    def populate(self):
        transfers = Transfer.objects.filter(
            network__symbol=self.network.symbol,
            block_hash='',
            source=Transfer.SELF
        ).exclude(trx_hash=None)

        for transfer in transfers:
            try:
                transaction_info = self.web3.eth.get_transaction_receipt(transfer.trx_hash)
            except Web3TransactionNotFound:
                continue
            transfer.block_number = transaction_info['blockNumber']
            transfer.block_hash = transaction_info['blockHash'].hex()
            transfer.save()


class AllPopulatorGetter:
    @classmethod
    def get(cls) -> List[BlockInfoPopulator]:
        return [
            TRXBlockInfoPopulator(get_tron_client()),
            Web3BlockInfoPopulator(get_web3_bsc_client(), Network.objects.get(symbol='BSC')),
            Web3BlockInfoPopulator(get_web3_eth_client(), Network.objects.get(symbol='ETH')),
        ]
