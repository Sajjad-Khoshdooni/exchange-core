import datetime
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import List

from django.db import transaction

from _helpers.blockchain.tron import get_tron_client
from ledger.models import Asset, Transfer, Network, DepositAddress
from tracker.blockchain.confirmer import Confirmer, MinimalBlockDTO
from tracker.blockchain.reverter import Reverter
from tracker.models.block_tracker import TRXBlockTracker

logger = logging.getLogger(__name__)

ETHER_CONTRACT_ID = '41a614f803b6fd780986a42c78ec9c7f77e6ded13c'

TRANSFER_METHOD_ID = 'a9059cbb'
TRANSFER_FROM_METHOD_ID = '23b872dd'

TRX_ADDRESS_PREFIX = '41'


def trxify_address(address: str):
    if len(address) == 42:
        return address
    if len(address) > 40:
        raise Exception

    number_of_zeros = 40 - len(address)
    return '41' + '0' * number_of_zeros + address


def decode_trx_data_in_block(data: str):
    method_id = data[:8]
    data = data[8:]
    if method_id == TRANSFER_METHOD_ID:
        address, amount = data[:64], data[64:]
        address = trxify_address(address.lstrip('0'))
        amount = Decimal(int(amount, 16)) / 10 ** 6
        return {'to': address, 'amount': amount}
    if method_id == TRANSFER_FROM_METHOD_ID:
        from_address, to_address, amount = data[:64], data[64:128], data[128:]
        from_address = trxify_address(from_address.lstrip('0'))
        to_address = trxify_address(to_address.lstrip('0'))
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
            t['raw_data']['contract'][0]['parameter']['value']['owner_address']
        ),
        'id': t['txID']
    }


@dataclass
class TransactionDTO:
    id: str
    amount: int
    from_address: str
    to_address: str


class CoinTRXHandler(ABC):
    @abstractmethod
    def is_valid_transaction(self, transaction):
        pass

    @abstractmethod
    def build_transaction_data(self, transaction) -> TransactionDTO:
        pass


class USDTCoinTRXHandler(CoinTRXHandler):
    def is_valid_transaction(self, t):
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
        decoded_data = decode_trx_data_in_block(t['raw_data']['contract'][0]['parameter']['value']['data'])
        return TransactionDTO(
            to_address=decoded_data['to'],
            amount=decoded_data['amount'],
            from_address=(
                decoded_data.get('from') or
                t['raw_data']['contract'][0]['parameter']['value']['owner_address']
            ),
            id=t['txID']
        )


class TRXCoinTRXHandler(CoinTRXHandler):
    def is_valid_transaction(self, t):
        return (
            len(t['ret']) == 1 and
            t['ret'][0]['contractRet'] == 'SUCCESS' and
            len(t['raw_data']['contract']) == 1 and
            t['raw_data']['contract'][0]['type'] == 'TransferContract'
        )

    def build_transaction_data(self, t):
        data = t['raw_data']['contract'][0]['parameter']['value']
        return TransactionDTO(
            to_address=data['to_address'],
            amount=data['amount'] / 10 ** 6,
            from_address=data['owner_address'],
            id=t['txID']
        )


class TRXTransferCreator:
    network = Network.objects.get(symbol='TRX')

    def __init__(self, coin_handlers: List[CoinTRXHandler]):
        self.coin_handlers = coin_handlers
        self.cache = {}

    def _get_fee_transaction_ids(self):
        if 'transaction_ids' not in self.cache:
            self.cache['transaction_ids'] = set(
                Transfer.objects.filter(
                    network=self.network,
                    is_fee=True
                ).values_list('trx_hash', flat=True)
            )
        return self.cache['transaction_ids']

    def _is_valid_transaction(self, t):
        return (
            t['txID'] not in self._get_fee_transaction_ids() and
            any(coin_handler.is_valid_transaction(t) for coin_handler in self.coin_handlers)
        )

    def from_block(self, block):
        block_hash = block['blockID']
        block_number = block['block_header']['raw_data']['number']
        asset = Asset.objects.get(symbol='USDT')

        raw_transactions = block.get('transactions', [])

        logger.info('Transactions %s' % len(raw_transactions))
        transactions = list(filter(self._is_valid_transaction, raw_transactions))
        logger.info('transactions reduced from %s to %s' % (len(raw_transactions), len(list(transactions))))

        parsed_transactions = []
        for t in transactions:
            for coin_handler in self.coin_handlers:
                if coin_handler.is_valid_transaction(t):
                    parsed_transactions.append(coin_handler.build_transaction_data(t))

        to_address_to_trx = {t.to_address: t for t in parsed_transactions}

        with transaction.atomic():
            to_deposit_addresses = DepositAddress.objects.filter(
                network=self.network,
                address__in=to_address_to_trx
            )

            for deposit_address in to_deposit_addresses:
                trx_data = to_address_to_trx[deposit_address.address]

                Transfer.objects.create(
                    deposit_address=deposit_address,
                    wallet=asset.get_wallet(deposit_address.account_secret.account),
                    network=self.network,
                    amount=trx_data.amount,
                    deposit=True,
                    trx_hash=trx_data.id,
                    block_hash=block_hash,
                    block_number=block_number,
                    out_address=trx_data.from_address
                )


class TRXRequester:
    def __init__(self, tron_client):
        self.tron = tron_client

    def get_latest_block(self):
        return self.tron.provider.make_request("wallet/getnowblock", {"visible": False})

    def get_block_by_id(self, _hash):
        return self.tron.get_block(_hash, visible=False)

    def get_block_by_number(self, number):
        return self.tron.get_block(number, visible=False)


class HistoryBuilder(ABC):
    @abstractmethod
    def build(self):
        pass


class TRXHistoryBuilder(HistoryBuilder):

    def __init__(self, requester, reverter, transfer_creator):
        self.requester = requester
        self.reverter = reverter
        self.transfer_creator = transfer_creator
        self.network = Network.objects.get(symbol='TRX')

    def build(self, only_add_now_block=False, maximum_block_step_for_backward=1000):
        block = self.requester.get_latest_block()
        if TRXBlockTracker.has(block['blockID']):
            return

        if only_add_now_block:
            self.add_block(block)
        elif (
            block['block_header']['raw_data']['number'] - TRXBlockTracker.get_latest_block().number
            >= maximum_block_step_for_backward
        ):
            self.forward_fulfill(block)
        else:
            self.backward_fulfill(block)

        confirmer = Confirmer(
            asset=Asset.objects.get(symbol='USDT'),
            network=self.network,
            block_tracker=TRXBlockTracker
        )
        confirmer.confirm(MinimalBlockDTO(hash=block['blockID'], number=block['block_header']['raw_data']['number']))

    def forward_fulfill(self, block):
        system_latest_block = TRXBlockTracker.get_latest_block()
        blockchain_latest_block_number = block['block_header']['raw_data']['number']

        _from = system_latest_block.number + 1
        _to = blockchain_latest_block_number - self.network.minimum_block_to_confirm

        for i in range(_from, _to):
            block = self.requester.get_block_by_number(i)
            self.add_block(block)

    def backward_fulfill(self, block):
        blocks = [block]

        while not TRXBlockTracker.has(blocks[-1]['block_header']['raw_data']['parentHash']):
            blocks.append(self.requester.get_block_by_id(blocks[-1]['block_header']['raw_data']['parentHash']))

        Reverter(TRXBlockTracker).from_number(blocks[-1]['block_header']['raw_data']['number'])
        for block in reversed(blocks):
            self.add_block(block)

    def add_block(self, block):
        self.transfer_creator.from_block(block)
        created_block = TRXBlockTracker.objects.create(
            number=block['block_header']['raw_data']['number'],
            hash=block['blockID'],
            block_date=datetime.datetime.fromtimestamp(block['block_header']['raw_data']['timestamp'] /
                                                       1000).astimezone(),
        )
        logger.info(f'(TRXHistoryBuilder) Block number: {created_block.number}, hash: {created_block.hash} created.')
