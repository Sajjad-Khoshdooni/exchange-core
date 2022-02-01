from tronpy import Tron

from accounts.models import Account
from ledger.models import Transfer, Network, Asset
from ledger.transaction_creator import TRXTransactionCreator
from wallet.models import Secret

tron = Tron()


class FeeHandler:
    def __init__(self, network: Network, asset: Asset):
        self.network = network
        self.asset = asset

    def get_asset_fee(self):
        if (
            self.asset.symbol != 'USDT' or self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        return 20 * 10 ** 6

    def is_balance_enough_for_fee(self, account: Account):
        if (
            self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        secret = account.accountsecret.secret
        secret.__class__ = Secret.get_secret_wallet(self.network.symbol)
        account_info = tron.get_account(secret.base58_address)
        return account_info.get('balance', 0) > self.get_asset_fee()

    def supply_fee_for_asset(self, fee_account: Account, account: Account):
        if (
            self.asset.symbol != 'TRX' or self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        crypto_wallet = account.accountsecret.secret
        crypto_wallet.__class__ = Secret.get_secret_wallet(self.network.symbol)

        fee_amount = self.get_asset_fee()
        trx_creator = TRXTransactionCreator(self.asset, crypto_wallet)
        transfer = Transfer.objects.create(
            deposit=False,
            network=self.network,
            wallet=self.asset.get_wallet(fee_account),
            amount=fee_amount,
            out_address=crypto_wallet.address,
        )
        trx_creator.from_transfer(transfer)
