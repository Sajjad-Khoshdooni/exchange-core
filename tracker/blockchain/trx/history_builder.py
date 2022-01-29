import datetime
import logging
from abc import ABC, abstractmethod

import base58
import requests
from django.db import transaction

from ledger.models import Asset, Transfer, Network, DepositAddress
from tracker.blockchain.confirmer import Confirmer, MinimalBlockDTO
from tracker.blockchain.reverter import Reverter
from tracker.models.block_tracker import TRXBlockTracker

logger = logging.getLogger(__name__)

ETHER_CONTRACT_ID = '41a614f803b6fd780986a42c78ec9c7f77e6ded13c'

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'

TRX_ADDRESS_PREFIX = '41'


class TooOldBlock(Exception):
    pass


def trxify_address(address):
    if len(address) == 42:
        return address
    if len(address) > 40:
        raise Exception

    number_of_zeros = 40 - len(address)
    return '41' + '0' * number_of_zeros + address


def base58_from_hex(hex_string):
    return base58.b58encode_check(bytes.fromhex(hex_string)).decode()


def decode_trx_data_in_block(data: str):
    method_id = data[:8]
    data = data[8:]
    if method_id == TRANSFER_METHOD_ID:
        address, amount = data[:64], data[64:]
        address = base58_from_hex(trxify_address(address.lstrip('0')))
        amount = int(amount, 16) / 10 ** 6
        return {'to': address, 'amount': amount}
    if method_id == TRANSFER_FROM_METHOD_ID:
        from_address, to_address, amount = data[:64], data[64:128], data[128:]
        from_address = base58_from_hex(trxify_address(from_address.lstrip('0')))
        to_address = base58_from_hex(trxify_address(to_address.lstrip('0')))
        amount = int(amount, 16) / 10 ** 6
        return {'from': from_address, 'to': to_address, 'amount': amount}
    raise NotImplementedError


def create_transaction_data(t):
    decoded_data = decode_trx_data_in_block(t['raw_data']['contract'][0]['parameter']['value']['data'])
    return {
        'to': decoded_data['to'],
        'amount': decoded_data['amount'],
        'from': (
            decoded_data.get('from') or
            base58_from_hex(t['raw_data']['contract'][0]['parameter']['value']['owner_address'])
        ),
        'id': t['txID']
    }


class TRXTransferCreator:
    def _is_valid_transaction(self, t):
        return (
            len(t['ret']) == 1 and
            t['ret'][0]['contractRet'] == 'SUCCESS' and
            len(t['raw_data']['contract']) == 1 and
            t['raw_data']['contract'][0]['type'] == 'TriggerSmartContract' and
            t['raw_data']['contract'][0]['parameter']['value']['contract_address'] == ETHER_CONTRACT_ID and
            t['raw_data']['contract'][0]['parameter']['value']['data'][:8] in [TRANSFER_METHOD_ID,
                                                                               TRANSFER_FROM_METHOD_ID]
        )

    def from_block(self, block):
        block_hash = block['blockID']
        block_number = block['block_header']['raw_data']['number']
        asset = Asset.objects.get(symbol='USDT')

        raw_transactions = block['transactions']

        logger.info('Transactions %s' % len(raw_transactions))
        transactions = list(filter(self._is_valid_transaction, raw_transactions))
        logger.info('transactions reduced from %s to %s' % (len(raw_transactions), len(list(transactions))))
        transactions = list(map(create_transaction_data, transactions))

        to_address_to_trx = {t['to']: t for t in transactions}

        with transaction.atomic():
            to_deposit_addresses = DepositAddress.objects.filter(
                schema__symbol=Network.TRX,
                address__in=to_address_to_trx
            )

            for deposit_address in to_deposit_addresses:
                trx_data = to_address_to_trx[deposit_address.address]

                Transfer.objects.create(
                    deposit_address=deposit_address,
                    wallet=asset.get_wallet(deposit_address.account),
                    amount=trx_data['amount'],
                    deposit=True,
                    trx_hash=trx_data['id'],
                    block_hash=block_hash,
                    block_number=block_number,
                    out_address=trx_data['from']
                )


class TRXRequester:
    def get_latest_block(self):
        url = "https://api.trongrid.io/wallet/getnowblock"
        headers = {"Accept": "application/json"}
        return requests.get(url, headers=headers).json()

    def get_block_by_id(self, _hash):
        url = "https://api.trongrid.io/wallet/getblockbyid"
        headers = {"Accept": "application/json"}
        data = {
            'value': _hash
        }
        return requests.post(url, json=data, headers=headers).json()


class HistoryBuilder(ABC):
    @abstractmethod
    def build(self):
        pass


class TRXHistoryBuilder(HistoryBuilder):
    def __init__(self, requester, reverter, transfer_creator):
        self.requester = requester
        self.reverter = reverter
        self.transfer_creator = transfer_creator

    def build(self, only_add_now_block=False, maximum_block_step=1000):
        block = self.requester.get_latest_block()
        if TRXBlockTracker.has(block['blockID']):
            return
        blocks = [block]

        if not only_add_now_block:
            while not TRXBlockTracker.has(blocks[-1]['block_header']['raw_data']['parentHash']):
                blocks.append(self.requester.get_block_by_id(blocks[-1]['block_header']['raw_data']['parentHash']))

                if len(blocks) > maximum_block_step:
                    raise TooOldBlock

        Reverter(TRXBlockTracker).from_number(blocks[-1]['block_header']['raw_data']['number'])
        for block in reversed(blocks):
            self.transfer_creator.from_block(block)
            TRXBlockTracker.objects.create(
                number=block['block_header']['raw_data']['number'],
                hash=block['blockID'],
                block_date=datetime.datetime.fromtimestamp(block['block_header']['raw_data']['timestamp'] / 1000),
            )
        confirmer = Confirmer(
            asset=Asset.objects.get(symbol='USDT'),
            network=Network.objects.get(symbol='TRX'),
            block_tracker=TRXBlockTracker
        )
        confirmer.confirm(MinimalBlockDTO(hash=block['blockID'], number=block['block_header']['raw_data']['number']))
