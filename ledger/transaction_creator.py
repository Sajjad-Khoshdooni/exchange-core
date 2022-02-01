from abc import ABC, abstractmethod

from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

from ledger.models import Transfer, Network, Asset
from wallet.models import TRXWallet, CryptoWallet


class TransactionCreationFailure(Exception):
    pass


class TransactionCreator(ABC):
    @abstractmethod
    def from_transfer(self, transfer: Transfer):
        pass


provider = HTTPProvider(api_key='d69566b0-4604-49b5-8066-d7441b3210ff')


class TRXTransactionCreator(TransactionCreator):
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

    def __init__(self, asset: Asset, wallet: TRXWallet, network='mainnet'):
        self.tron = Tron(provider=provider, network=network)

        self.asset = asset
        self.wallet = wallet

    def from_transfer(self, transfer: Transfer):
        if self.asset.symbol == 'TRX':
            return self._trx_from_transfer(transfer)
        elif self.asset.symbol == 'USDT':
            return self._smart_contract_from_transfer(transfer)
        raise NotImplementedError

    def _smart_contract_from_transfer(self, transfer: Transfer):
        contract = self.tron.get_contract(self.USDT_CONTRACT)
        transaction = (
            contract.functions.transfer(transfer.out_address, transfer.amount * 10 ** 6)
                .with_owner(self.wallet.address)
                .fee_limit(10_000_000)
                .build()
                .sign(self._private_key)
        )
        result = transaction.broadcast()
        if not result.get('result', False):
            raise TransactionCreationFailure

        return result['txid']

    def _trx_from_transfer(self, transfer: Transfer):
        transaction = (
            self.tron.trx.transfer(self.wallet.address, transfer.out_address, transfer.amount * 10 ** 6)
                .build()
                .sign(self._private_key)
        )
        result = transaction.broadcast()

        if not result.get('result', False):
            raise TransactionCreationFailure

        return result['txid']

    @property
    def _private_key(self):
        return PrivateKey(bytes.fromhex(self.wallet.key[2:]))  # Ignore first 0x


class TransactionCreatorBuilder:
    NETWORK_TO_TRANSACTION_CREATOR = {
        Network.TRX: TRXTransactionCreator
    }

    def __init__(self, network: Network, asset: Asset, wallet: CryptoWallet):
        self.network = network
        self.asset = asset
        self.wallet = wallet

    def build(self) -> TransactionCreator:
        if self.network.symbol not in self.NETWORK_TO_TRANSACTION_CREATOR:
            raise NotImplementedError
        return self.NETWORK_TO_TRANSACTION_CREATOR[self.network.symbol](self.asset, self.wallet)
