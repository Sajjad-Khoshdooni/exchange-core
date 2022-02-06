from typing import List

from web3 import Web3
from web3.middleware import geth_poa_middleware
from web3.types import BlockData

from ledger.models import Asset
from tracker.blockchain.dtos import BlockDTO, RawTransactionDTO, TransactionDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.transfer_creator import TransactionParser, CoinHandler


class BSCCoinBSCHandler(CoinHandler):
    def __init__(self):
        self.asset = Asset.objects.get(symbol='BNB')

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            t['input'] == '0x' and
            t['to'] is not None
        )

    def build_transaction_data(self, t):
        t = t.raw_transaction
        return TransactionDTO(
            to_address=t['to'].lower(),
            amount=t['value'] / 10 ** 18,
            from_address=t['from'].lower(),
            id=t['hash'].hex(),
            asset=self.asset
        )


class BSCTransactionParser(TransactionParser):

    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        return [RawTransactionDTO(
            id=t['hash'].hex().lower(),
            raw_transaction=t
        ) for t in block.raw_block.get('transactions', [])]


class BSCRequester(Requester):
    def __init__(self, bsc_web3):
        self.web3 = bsc_web3

    @staticmethod
    def build_block_dto_from_dict(data: BlockData) -> BlockDTO:
        return BlockDTO(
            id=data['hash'].hex().lower(),
            number=data['number'],
            parent_id=data['parentHash'].hex().lower(),
            timestamp=data['timestamp'],
            raw_block=data
        )

    def get_latest_block(self):
        return self.build_block_dto_from_dict(
            self.web3.eth.get_block('latest', full_transactions=True)
        )

    def get_block_by_id(self, _hash):
        return self.build_block_dto_from_dict(self.web3.eth.get_block(_hash, full_transactions=True))

    def get_block_by_number(self, number):
        return self.build_block_dto_from_dict(self.web3.eth.get_block(number, full_transactions=True))
