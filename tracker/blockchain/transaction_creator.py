from abc import ABC, abstractmethod

from tronpy import Tron
from tronpy.keys import PrivateKey

from ledger.models import Transfer, Network, Asset
from wallet.models import TRXWallet


class TransactionCreationFailure(Exception):
    pass


class TransactionCreator(ABC):
    @abstractmethod
    def from_transfer(self, transfer: Transfer):
        pass


class TRXTransactionCreator(TransactionCreator):
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

    def __init__(self, asset: Asset, wallet: TRXWallet, network='mainnet'):
        self.tron = Tron(network=network)

        self.asset = asset
        self.wallet = wallet

    def from_transfer(self, transfer: Transfer):
        if self.asset.symbol != 'USDT':
            raise NotImplementedError

        contract = self.tron.get_contract(self.USDT_CONTRACT)
        transaction = (
            contract.functions.transfer(transfer.out_address, transfer.amount * 10 ** 6)
                .with_owner(self.wallet.address)
                .fee_limit(5_000_000)
                .build()
                .sign(PrivateKey(bytes.fromhex(self.wallet.key)))
        )
        result = transaction.broadcast()
        if not result.get('result', False):
            raise TransactionCreationFailure

        return result['txid']


class TransactionCreatorBuilder:
    NETWORK_TO_TRANSACTION_CREATOR = {
        Network.TRX: TRXTransactionCreator
    }

    def __init__(self, network: Network, asset: Asset, wallet: TRXWallet):
        self.network = network
        self.asset = asset
        self.wallet = wallet

    def build(self) -> TransactionCreator:
        if self.network.symbol not in self.NETWORK_TO_TRANSACTION_CREATOR:
            raise NotImplementedError
        return self.NETWORK_TO_TRANSACTION_CREATOR[self.network.symbol](self.asset, self.wallet)
