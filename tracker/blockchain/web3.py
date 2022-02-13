from typing import List

from web3 import Web3
from web3.types import BlockData

from ledger.amount_normalizer import AmountNormalizer
from ledger.models import Asset
from ledger.symbol_contract_mapper import SymbolContractMapper
from tracker.blockchain.abi_getter import AbiGetter
from tracker.blockchain.dtos import BlockDTO, RawTransactionDTO, TransactionDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.transfer_creator import TransactionParser, CoinHandler

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'


class Web3BaseNetworkCoinHandler(CoinHandler):
    def __init__(self, base_network_asset: Asset, amount_normalizer: AmountNormalizer):
        self.asset = base_network_asset
        self.amount_normalizer = amount_normalizer

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
            amount=self.amount_normalizer.from_int_to_decimal(t['value']),
            from_address=t['from'].lower(),
            id=t['hash'].hex(),
            asset=self.asset
        )


class Web3ERC20BasedCoinHandler(CoinHandler):

    def __init__(self,
                 web3_client: Web3,
                 symbol_contract_mapper: SymbolContractMapper,
                 amount_normalizer: AmountNormalizer,
                 abi_getter: AbiGetter
                 ):
        self.web3 = web3_client
        self.symbol_contract_mapper = symbol_contract_mapper
        self.amount_normalizer = amount_normalizer
        self.abi_getter = abi_getter
        self.all_asset_symbols = Asset.objects.all().values_list('symbol', flat=True)

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            t['to'] and
            t['to'].lower() in self.symbol_contract_mapper.list_of_contracts() and
            t['input'][2:10] in [TRANSFER_METHOD_ID, TRANSFER_FROM_METHOD_ID] and
            self.symbol_contract_mapper.get_symbol_of_contract(t['to'].lower()) in self.all_asset_symbols
        )

    def get_asset(self, t):
        if symbol := self.symbol_contract_mapper.get_symbol_of_contract(t['to'].lower()):
            return Asset.objects.get(symbol=symbol)
        raise NotImplementedError

    def build_transaction_data(self, t):
        t = t.raw_transaction

        contract = self.web3.eth.contract(self.web3.toChecksumAddress(t['to'].lower()),
                                          abi=self.abi_getter.from_contract(t['to'].lower()))
        function, decoded_input = contract.decode_function_input(t['input'])
        if function.function_identifier == 'transfer':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=self.amount_normalizer.from_int_to_decimal(decoded_input['amount']),
                from_address=t['from'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )
        if function.function_identifier == 'transferFrom':
            return TransactionDTO(
                to_address=decoded_input['recipient'].lower(),
                amount=self.amount_normalizer.from_int_to_decimal(decoded_input['amount']),
                from_address=decoded_input['sender'].lower(),
                id=t['hash'].hex(),
                asset=self.get_asset(t)
            )


class Web3TransactionParser(TransactionParser):

    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        return [RawTransactionDTO(
            id=t['hash'].hex().lower(),
            raw_transaction=t
        ) for t in block.raw_block.get('transactions', [])]


class Web3Requester(Requester):
    def __init__(self, web3_client: Web3):
        self.web3 = web3_client

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