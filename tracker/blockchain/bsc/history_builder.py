from typing import List

from web3 import Web3
from web3.types import BlockData

from _helpers.blockchain.bsc import get_web3_bsc_client, bsc
from ledger.consts import BEP20_SYMBOL_TO_SMART_CONTRACT
from ledger.models import Asset
from tracker.blockchain.dtos import BlockDTO, RawTransactionDTO, TransactionDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.transfer_creator import TransactionParser, CoinHandler

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'



# TODO: check XLM


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


class BEP20CoinBSCHandler(CoinHandler):

    def __init__(self):
        self.web3 = get_web3_bsc_client()
        self.smart_contract_to_symbol = {v: k for k, v in BEP20_SYMBOL_TO_SMART_CONTRACT.items()}
        self.all_asset_symbols = Asset.objects.all().values_list('symbol', flat=True)

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            t['to'] and
            t['to'].lower() in BEP20_SYMBOL_TO_SMART_CONTRACT.values() and
            t['input'][2:10] in [TRANSFER_METHOD_ID, TRANSFER_FROM_METHOD_ID] and
            self.smart_contract_to_symbol.get(t['to'].lower()) in self.all_asset_symbols
        )

    def get_asset(self, t):
        if symbol := self.smart_contract_to_symbol.get(t['to'].lower()):
            return Asset.objects.get(symbol=symbol)
        raise NotImplementedError

    def build_transaction_data(self, t):
        t = t.raw_transaction

        contract = self.web3.eth.contract(self.web3.toChecksumAddress(t['to'].lower()),
                                          abi=bsc.get_bsc_abi(t['to'].lower()))
        function, decoded_input = contract.decode_function_input(t['input'])
        if function.function_identifier == 'transfer':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=decoded_input['amount'] / 10 ** 18,
                from_address=t['from'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )
        if function.function_identifier == 'transferFrom':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=decoded_input['amount'] / 10 ** 18,
                from_address=decoded_input['sender'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )


class BSCTransactionParser(TransactionParser):

    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        return [RawTransactionDTO(
            id=t['hash'].hex().lower(),
            raw_transaction=t
        ) for t in block.raw_block.get('transactions', [])]


class BSCRequester(Requester):
    def __init__(self, bsc_web3: Web3):
        self.web3 = bsc_web3

    @staticmethod
    def build_block_dto_from_dict(data: BlockData) -> BlockDTO:
        return BlockDTO(
            id=data['hash'].hex().lower(),
            number=data['number'],
            parent_id=data['parentHash'].hex().lower(),
            timestamp=data['timestamp'] * 1000,
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
