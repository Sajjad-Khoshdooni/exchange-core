import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List

from django.db import transaction

from ledger.models import Transfer, DepositAddress, Network
from tracker.blockchain.dtos import RawTransactionDTO, TransactionDTO, BlockDTO

logger = logging.getLogger(__name__)


class CoinHandler(ABC):
    @abstractmethod
    def is_valid_transaction(self, t: RawTransactionDTO):
        pass

    @abstractmethod
    def build_transaction_data(self, t: RawTransactionDTO) -> TransactionDTO:
        pass


class TransactionParser(ABC):

    @abstractmethod
    def list_of_raw_transaction_from_block(self, block: BlockDTO) -> List[RawTransactionDTO]:
        pass


class TransferCreator:

    def __init__(self, network: Network, coin_handlers: List[CoinHandler], transaction_parser: TransactionParser):
        self.coin_handlers = coin_handlers
        self.cache = {}
        self.network = network
        self.transaction_parser = transaction_parser

    def _get_fee_transaction_ids(self):
        if 'transaction_ids' not in self.cache:
            self.cache['transaction_ids'] = set(
                Transfer.objects.filter(
                    network=self.network,
                    is_fee=True
                ).values_list('trx_hash', flat=True)
            )
        return self.cache['transaction_ids']

    def _is_valid_transaction(self, t: RawTransactionDTO):
        return (
            t.id not in self._get_fee_transaction_ids() and
            any(coin_handler.is_valid_transaction(t) for coin_handler in self.coin_handlers)
        )

    def from_block(self, block: BlockDTO):
        block_hash = block.id
        block_number = block.number

        raw_transactions = self.transaction_parser.list_of_raw_transaction_from_block(block)

        logger.info('Transactions %s' % len(raw_transactions))
        transactions = list(filter(self._is_valid_transaction, raw_transactions))
        logger.info('transactions reduced from %s to %s' % (len(raw_transactions), len(list(transactions))))

        parsed_transactions = []
        for t in transactions:
            count = 0

            for coin_handler in self.coin_handlers:
                if coin_handler.is_valid_transaction(t):
                    transaction_data = coin_handler.build_transaction_data(t)

                    if transaction_data:
                        count += 1
                        parsed_transactions.append(transaction_data)

            if count > 1:
                logger.warning(
                    'transaction is valid in more than one coin handler',
                    extra={'transaction': t.id, 'network': self.network.symbol}
                )

        recipient_address_to_transactions = defaultdict(list)

        for t in parsed_transactions:
            recipient_address_to_transactions[t.to_address].append(t)

        with transaction.atomic():
            to_deposit_addresses = DepositAddress.objects.filter(
                network=self.network,
                address__in=recipient_address_to_transactions
            )

            for deposit_address in to_deposit_addresses:
                for trx_data in recipient_address_to_transactions[deposit_address.address]:
                    Transfer.objects.create(
                        status=Transfer.PENDING,
                        deposit_address=deposit_address,
                        wallet=trx_data.asset.get_wallet(deposit_address.account_secret.account),
                        network=self.network,
                        amount=trx_data.amount,
                        deposit=True,
                        trx_hash=trx_data.id,
                        block_hash=block_hash,
                        block_number=block_number,
                        out_address=trx_data.from_address
                    )
