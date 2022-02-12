from abc import ABC, abstractmethod

from tronpy.keys import PrivateKey

from _helpers.blockchain.bsc import get_web3_bsc_client, bsc
from _helpers.blockchain.tron import get_tron_client
from ledger.amount_normalizer import AmountNormalizer
from ledger.consts import BEP20_SYMBOL_TO_SMART_CONTRACT
from ledger.models import Transfer, Network, Asset
from wallet.models import TRXWallet, CryptoWallet, ETHWallet


class TransactionCreationFailure(Exception):
    pass


class TransactionCreator(ABC):
    @abstractmethod
    def from_transfer(self, transfer: Transfer):
        pass


class TRXTransactionCreator(TransactionCreator):
    USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

    def __init__(self, asset: Asset, wallet: TRXWallet):
        self.tron = get_tron_client()

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
            contract.functions.transfer(transfer.out_address, int(transfer.amount * 10 ** 6))
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
            self.tron.trx.transfer(self.wallet.address, transfer.out_address, int(transfer.amount * 10 ** 6))
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


class BSCTransactionCreator(TransactionCreator):

    def __init__(self, asset: Asset, wallet: ETHWallet):
        self.asset = asset
        self.wallet = wallet
        self.web3 = get_web3_bsc_client()

    def from_transfer(self, transfer: Transfer):
        if self.asset.symbol == 'BNB':
            return self.bnb_from_transfer(transfer)
        return self.smart_contract_from_transfer(transfer)

    def bnb_from_transfer(self, transfer: Transfer):
        nonce = self.web3.eth.getTransactionCount(self.web3.toChecksumAddress(self.wallet.address))
        tx = {
            'nonce': nonce,
            'to': self.web3.toChecksumAddress(transfer.out_address),
            'value': self.web3.toWei(transfer.amount, 'ether'),
            'gas': 21_000,
            'gasPrice': self.web3.toWei('5', 'gwei')
        }
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.wallet.key)

        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return tx_hash.hex()

    def smart_contract_from_transfer(self, transfer):
        if self.asset.symbol not in BEP20_SYMBOL_TO_SMART_CONTRACT:
            raise NotImplementedError
        smart_contract = BEP20_SYMBOL_TO_SMART_CONTRACT[self.asset.symbol]
        contract = self.web3.eth.contract(self.web3.toChecksumAddress(smart_contract),
                                          abi=bsc.get_bsc_abi(smart_contract))
        nonce = self.web3.eth.getTransactionCount(self.web3.toChecksumAddress(self.wallet.address))
        normalizer = AmountNormalizer(network=Network.objects.get(symbol='BSC'), asset=self.asset)
        tx = contract.functions.transfer(
            self.web3.toChecksumAddress(transfer.out_address), normalizer.from_decimal_to_int(transfer.amount)
        ).buildTransaction(
            {'nonce': nonce, 'gas': 30_000, 'gasPrice': self.web3.toWei('5', 'gwei')}
        )

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.wallet.key)

        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return tx_hash.hex()


class TransactionCreatorBuilder:
    NETWORK_TO_TRANSACTION_CREATOR = {
        Network.TRX: TRXTransactionCreator,
        Network.BSC: BSCTransactionCreator
    }

    def __init__(self, network: Network, asset: Asset, wallet: CryptoWallet):
        self.network = network
        self.asset = asset
        self.wallet = wallet

    def build(self) -> TransactionCreator:
        if self.network.symbol not in self.NETWORK_TO_TRANSACTION_CREATOR:
            raise NotImplementedError
        return self.NETWORK_TO_TRANSACTION_CREATOR[self.network.symbol](self.asset, self.wallet)
