from abc import ABC, abstractmethod

from tronpy.keys import PrivateKey
from web3 import Web3

from _helpers.blockchain.bsc import get_web3_bsc_client
from _helpers.blockchain.eth import get_web3_eth_client
from _helpers.blockchain.tron import get_tron_client
from ledger.amount_normalizer import AmountNormalizer
from ledger.consts import DEFAULT_COIN_OF_NETWORK
from ledger.models import Transfer, Network, Asset
from ledger.symbol_contract_mapper import (
    SymbolContractMapper, bep20_symbol_contract_mapper,
    erc20_symbol_contract_mapper,
)
from tracker.blockchain.abi_getter import AbiGetter, bsc_abi_getter, eth_abi_getter
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


class Web3TransactionCreator(TransactionCreator):

    def __init__(
        self,
        asset: Asset,
        network: Network,
        wallet: ETHWallet,
        web3_client: Web3,
        abi_getter: AbiGetter,
        symbol_contract_mapper: SymbolContractMapper
    ):
        self.asset = asset
        self.network = network
        self.wallet = wallet
        self.web3 = web3_client
        self.abi_getter = abi_getter
        self.symbol_contract_mapper = symbol_contract_mapper

    def from_transfer(self, transfer: Transfer):
        if self.asset.symbol == DEFAULT_COIN_OF_NETWORK[self.network.symbol]:
            return self.base_coin_from_transfer(transfer)
        return self.smart_contract_from_transfer(transfer)

    def base_coin_from_transfer(self, transfer: Transfer):
        nonce = self.web3.eth.getTransactionCount(self.web3.toChecksumAddress(self.wallet.address))
        tx = {
            'nonce': nonce,
            'to': self.web3.toChecksumAddress(transfer.out_address),
            'value': self.web3.toWei(transfer.amount, 'ether'),
            'gas': 21_000,
            'gasPrice': self.web3.toWei('5', 'gwei')  # todo: eth gas price is around 64. this is for only bsc
        }
        signed_tx = self.web3.eth.account.sign_transaction(tx, self.wallet.key)

        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return tx_hash.hex()

    def smart_contract_from_transfer(self, transfer):
        if self.asset.symbol not in self.symbol_contract_mapper.list_of_symbols():
            raise NotImplementedError
        smart_contract = self.symbol_contract_mapper.get_contract_of_symbol(self.asset.symbol)
        contract = self.web3.eth.contract(self.web3.toChecksumAddress(smart_contract),
                                          abi=self.abi_getter.from_contract(smart_contract))
        nonce = self.web3.eth.getTransactionCount(self.web3.toChecksumAddress(self.wallet.address))
        normalizer = AmountNormalizer(network=self.network, asset=self.asset)
        tx = contract.functions.transfer(
            self.web3.toChecksumAddress(transfer.out_address), normalizer.from_decimal_to_int(transfer.amount)
        ).buildTransaction(
            {'nonce': nonce, 'gas': 30_000, 'gasPrice': self.web3.toWei('5', 'gwei')}  # todo: eth gas price is around 64. this is for only bsc
        )

        signed_tx = self.web3.eth.account.sign_transaction(tx, self.wallet.key)

        tx_hash = self.web3.eth.sendRawTransaction(signed_tx.rawTransaction)

        return tx_hash.hex()


class TransactionCreatorBuilder:
    def __init__(self, network: Network, asset: Asset, wallet: CryptoWallet):
        self.network = network
        self.asset = asset
        self.wallet = wallet

    def build(self) -> TransactionCreator:
        if self.network.symbol == 'TRX':
            return TRXTransactionCreator(self.asset, self.wallet)
        if self.network.symbol == 'BSC':
            return Web3TransactionCreator(
                asset=self.asset,
                network=self.network,
                wallet=self.wallet,
                web3_client=get_web3_bsc_client(),
                abi_getter=bsc_abi_getter,
                symbol_contract_mapper=bep20_symbol_contract_mapper
            )
        if self.network.symbol == 'ETH':
            return Web3TransactionCreator(
                asset=self.asset,
                network=self.network,
                wallet=self.wallet,
                web3_client=get_web3_eth_client(),
                abi_getter=eth_abi_getter,
                symbol_contract_mapper=erc20_symbol_contract_mapper
            )
        raise NotImplementedError
