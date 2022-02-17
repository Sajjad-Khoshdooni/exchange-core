from abc import ABC, abstractmethod
from decimal import Decimal

from tronpy import Tron
from tronpy.exceptions import AddressNotFound
from web3 import Web3

from _helpers.blockchain.bsc import get_web3_bsc_client
from _helpers.blockchain.eth import get_web3_eth_client
from _helpers.blockchain.tron import get_tron_client
from tracker.blockchain.amount_normalizer import AmountNormalizer
from ledger.models import Asset, DepositAddress, Network
from ledger.symbol_contract_mapper import (
    SymbolContractMapper, bep20_symbol_contract_mapper,
    erc20_symbol_contract_mapper,
)
from tracker.blockchain.abi_getter import AbiGetter, bsc_abi_getter, eth_abi_getter


class CryptoAccountBalanceGetter(ABC):

    @abstractmethod
    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> Decimal:
        pass


class TronAccountBalanceGetter(CryptoAccountBalanceGetter):
    NETWORK_COIN = 'TRX'

    ASSET_TO_SMART_CONTACT = {
        'USDT': "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    }

    def __init__(self, tron_client: Tron):
        self.tron = tron_client
        self.network = Network.objects.get(symbol='TRX')

    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> Decimal:
        normalizer = AmountNormalizer(network=self.network)
        if asset.symbol == self.NETWORK_COIN:
            return Decimal(self.get_network_coin_balance(deposit_address))
        else:
            return normalizer.from_int_to_decimal(
                asset=asset,
                amount=self.get_smart_contact_balance(deposit_address, asset)
            )

    def get_network_coin_balance(self, deposit_address: DepositAddress):
        try:
            return self.tron.get_account_balance(deposit_address.address)
        except AddressNotFound:
            return 0

    def get_smart_contact_balance(self, deposit_address: DepositAddress, asset: Asset):
        smart_contact = self.ASSET_TO_SMART_CONTACT[asset.symbol]
        contract = self.tron.get_contract(smart_contact)
        return contract.functions.balanceOf(deposit_address.address)


class Web3AccountBalanceGetter(CryptoAccountBalanceGetter):
    def __init__(self,
                 web3_client: Web3,
                 network: Network,
                 network_asset: Asset,
                 symbol_contract_mapper: SymbolContractMapper,
                 abi_getter: AbiGetter,
                 ):
        self.web3 = web3_client
        self.network = network
        self.network_asset = network_asset
        self.symbol_contract_mapper = symbol_contract_mapper
        self.abi_getter = abi_getter

    def get_asset_of_account(self, deposit_address: DepositAddress, asset: Asset) -> Decimal:
        normalizer = AmountNormalizer(network=self.network)
        if asset.symbol == self.network_asset.symbol:
            return normalizer.from_int_to_decimal(
                asset=asset,
                amount=self.get_network_coin_balance(deposit_address)
            )
        else:
            return normalizer.from_int_to_decimal(
                asset=asset,
                amount=self.get_smart_contact_balance(deposit_address, asset)
            )

    def get_network_coin_balance(self, deposit_address: DepositAddress):
        return self.web3.eth.get_balance(self.web3.toChecksumAddress(deposit_address.address))

    def get_smart_contact_balance(self, deposit_address: DepositAddress, asset: Asset):
        smart_contact = self.symbol_contract_mapper.get_contract_of_symbol(asset.symbol)

        contract = self.web3.eth.contract(self.web3.toChecksumAddress(smart_contact),
                                          abi=self.abi_getter.from_contract(smart_contact))
        return contract.functions.balanceOf(self.web3.toChecksumAddress(deposit_address.address)).call()


class CryptoAccountBalanceGetterFactory:
    @staticmethod
    def build(network: Network):
        if network.symbol == 'TRX':
            return TronAccountBalanceGetter(get_tron_client())
        if network.symbol == 'BSC':
            return Web3AccountBalanceGetter(
                web3_client=get_web3_bsc_client(),
                network=network,
                network_asset=Asset.objects.get(symbol='BNB'),
                symbol_contract_mapper=bep20_symbol_contract_mapper,
                abi_getter=bsc_abi_getter
            )
        if network.symbol == 'ETH':
            return Web3AccountBalanceGetter(
                web3_client=get_web3_eth_client(),
                network=network,
                network_asset=Asset.objects.get(symbol='ETH'),
                symbol_contract_mapper=erc20_symbol_contract_mapper,
                abi_getter=eth_abi_getter
            )
        raise NotImplementedError
