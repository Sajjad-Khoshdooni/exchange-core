import logging
from abc import abstractmethod
from decimal import Decimal
from typing import List

from tronpy import Tron

from ledger.models import Asset
from tracker.blockchain.history_builder import BlockDTO
from tracker.blockchain.requester import Requester
from tracker.blockchain.transfer_creator import CoinHandler, TransactionDTO, TransactionParser, RawTransactionDTO

logger = logging.getLogger(__name__)

ETHER_CONTRACT_ID = '41a614f803b6fd780986a42c78ec9c7f77e6ded13c'

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'

TRX_ADDRESS_PREFIX = '41'


class AddressIsNotValid(Exception):
    pass


class BuildTransactionError(Exception):
    pass


def trxify_address(address: str):
    if len(address) == 42:
        return address
    if len(address) > 40:
        address = address[-40:]

    number_of_zeros = 40 - len(address)
    return '41' + '0' * number_of_zeros + address


def decode_trx_data_in_block(data: str):
    method_id = data[:8]
    data = data[8:]
    if method_id == TRANSFER_METHOD_ID:
        address, amount = data[:64], data[64:]
        address = trxify_address(address.lstrip('0'))

        if amount:
            amount = Decimal(int(amount, 16)) / 10 ** 6
        else:
            amount = 0

        return {'to': address, 'amount': amount}
    if method_id == TRANSFER_FROM_METHOD_ID:
        from_address, to_address, amount = data[:64], data[64:128], data[128:]
        from_address = trxify_address(from_address.lstrip('0'))
        to_address = trxify_address(to_address.lstrip('0'))

        if amount:
            amount = int(amount, 16) / 10 ** 6
        else:
            amount = 0

        return {'from': from_address, 'to': to_address, 'amount': amount}
    raise NotImplementedError


class USDTCoinTRXHandler(CoinHandler):
    def __init__(self):
        self.asset = Asset.objects.get(symbol='USDT')

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            len(t['ret']) == 1 and
            t['ret'][0]['contractRet'] == 'SUCCESS' and
            len(t['raw_data']['contract']) == 1 and
            t['raw_data']['contract'][0]['type'] == 'TriggerSmartContract' and
            t['raw_data']['contract'][0]['parameter']['value']['contract_address'] == ETHER_CONTRACT_ID and
            t['raw_data']['contract'][0]['parameter']['value']['data'][:8] in [TRANSFER_METHOD_ID,
                                                                               TRANSFER_FROM_METHOD_ID]
        )

    def build_transaction_data(self, t):
        t = t.raw_transaction
        try:
            decoded_data = decode_trx_data_in_block(t['raw_data']['contract'][0]['parameter']['value']['data'])
        except AddressIsNotValid as e:
            raise BuildTransactionError(f'Address is not valid for txid: {t["txID"]}')
        return TransactionDTO(
            to_address=decoded_data['to'],
            amount=decoded_data['amount'],
            from_address=(
                decoded_data.get('from') or
                t['raw_data']['contract'][0]['parameter']['value']['owner_address']
            ),
            id=t['txID'],
            asset=self.asset
        )


class TRXCoinTRXHandler(CoinHandler):
    def __init__(self):
        self.asset = Asset.objects.get(symbol='TRX')

    def is_valid_transaction(self, t):
        t = t.raw_transaction
        return (
            len(t['ret']) == 1 and
            t['ret'][0]['contractRet'] == 'SUCCESS' and
            len(t['raw_data']['contract']) == 1 and
            t['raw_data']['contract'][0]['type'] == 'TransferContract'
        )

    def build_transaction_data(self, t):
        t = t.raw_transaction
        data = t['raw_data']['contract'][0]['parameter']['value']
        return TransactionDTO(
            to_address=data['to_address'],
            amount=data['amount'] / 10 ** 6,
            from_address=data['owner_address'],
            id=t['txID'],
            asset=self.asset
        )


class TRXTransactionParser(TransactionParser):

    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        return [RawTransactionDTO(
            id=t['txID'],
            raw_transaction=t
        ) for t in block.raw_block.get('transactions', [])]


class TRXRequester(Requester):
    def __init__(self, tron_client: Tron):
        self.tron = tron_client

    @staticmethod
    def build_block_dto_from_dict(data) -> BlockDTO:
        return BlockDTO(
            id=data['blockID'],
            number=data['block_header']['raw_data']['number'],
            parent_id=data['block_header']['raw_data']['parentHash'],
            timestamp=data['block_header']['raw_data']['timestamp'],
            raw_block=data
        )

    def get_latest_block(self):
        return self.build_block_dto_from_dict(
            self.tron.provider.make_request("wallet/getnowblock", {"visible": False})
        )

    def get_block_by_id(self, _hash):
        return self.build_block_dto_from_dict(self.tron.get_block(_hash, visible=False))

    def get_block_by_number(self, number):
        return self.build_block_dto_from_dict(self.tron.get_block(number, visible=False))

    def get_asset_balance_of_account(self, address, asset):
        if asset.symbol == 'TRX':
            return self.tron.get_account_balance(address)

        asset_symbol_to_token_id = {
            'USDT': None
        }

        if asset.symbol not in asset_symbol_to_token_id:
            raise NotImplementedError
        return self.tron.get_account_asset_balance(address, asset_symbol_to_token_id[asset.symbol])
