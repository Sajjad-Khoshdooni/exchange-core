from abc import ABC, abstractmethod

from tronpy import Tron
from web3 import Web3

from _helpers.blockchain.bsc import bsc, get_web3_bsc_client
from _helpers.blockchain.tron import get_tron_client
from ledger.amount_normalizer import NormalizedAmount, AmountNormalizer
from ledger.models import Asset, DepositAddress, Network


class CryptoAccountBalanceGetter(ABC):

    @abstractmethod
    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> NormalizedAmount:
        pass


class TronAccountBalanceGetter(CryptoAccountBalanceGetter):
    NETWORK_COIN = 'TRX'

    ASSET_TO_SMART_CONTACT = {
        'USDT': "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    }

    def __init__(self, tron_client: Tron):
        self.tron = tron_client
        self.network = Network.objects.get(symbol='TRX')

    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> NormalizedAmount:
        normalizer = AmountNormalizer(network=self.network, asset=asset)
        if asset.symbol == self.NETWORK_COIN:
            return NormalizedAmount(self.get_network_coin_balance(deposit_address))
        else:
            return normalizer.from_int_to_decimal(self.get_smart_contact_balance(deposit_address, asset))

    def get_network_coin_balance(self, deposit_address: DepositAddress):
        return self.tron.get_account_balance(deposit_address.address)

    def get_smart_contact_balance(self, deposit_address: DepositAddress, asset: Asset):
        smart_contact = self.ASSET_TO_SMART_CONTACT[asset.symbol]
        contract = self.tron.get_contract(smart_contact)
        return contract.functions.balanceOf(deposit_address.address)


class BSCAccountBalanceGetter(CryptoAccountBalanceGetter):
    NETWORK_COIN = 'BNB'

    ASSET_TO_SMART_CONTACT = {
        'USDT': "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    }

    def __init__(self, web3_client: Web3):
        self.web3 = web3_client
        self.network = Network.objects.get(symbol='BSC')

    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> NormalizedAmount:
        normalizer = AmountNormalizer(network=self.network, asset=asset)
        if asset.symbol == self.NETWORK_COIN:
            return normalizer.from_int_to_decimal(self.get_network_coin_balance(deposit_address))
        else:
            return normalizer.from_int_to_decimal(self.get_smart_contact_balance(deposit_address, asset))

    def get_network_coin_balance(self, deposit_address: DepositAddress):
        return self.web3.eth.get_balance(self.web3.toChecksumAddress(deposit_address.address))

    def get_smart_contact_balance(self, deposit_address: DepositAddress, asset: Asset):
        smart_contact = self.ASSET_TO_SMART_CONTACT[asset.symbol]

        contract = self.web3.eth.contract(self.web3.toChecksumAddress(smart_contact),
                                          abi=bsc.get_bsc_abi(smart_contact))
        return contract.functions.balanceOf(deposit_address.address).call()


class CryptoAccountBalanceGetterFactory:
    @staticmethod
    def build(network: Network):
        if network.symbol == 'TRX':
            return TronAccountBalanceGetter(get_tron_client())
        if network.symbol == 'BSC':
            return BSCAccountBalanceGetter(get_web3_bsc_client())
        raise NotImplementedError
