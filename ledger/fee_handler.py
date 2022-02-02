from tronpy.exceptions import AddressNotFound

from _helpers.blockchain.tron import get_tron_client
from accounts.models import Account
from ledger.models import Transfer, Network, Asset
from ledger.transaction_creator import TRXTransactionCreator
from wallet.models import Secret

tron = get_tron_client()


class FeeHandler:
    def __init__(self, network: Network, asset: Asset):
        self.network = network
        self.asset = asset

    def get_asset_fee(self):
        if (
            self.asset.symbol != 'USDT' or self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        return 10

    def is_balance_enough_for_fee(self, account: Account):
        if (
            self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        secret = account.accountsecret.secret
        secret.__class__ = Secret.get_secret_wallet(self.network.symbol)

        try:
            account_info = tron.get_account(secret.base58_address)
        except AddressNotFound:
            return False

        return account_info.get('balance', 0) >= self.get_asset_fee() * 10 ** 6

    def supply_fee_for_asset(self, fee_account: Account, account: Account):
        if (
            self.asset.symbol != 'USDT' or self.network.symbol != 'TRX'
        ):
            raise NotImplementedError
        sender_wallet = fee_account.accountsecret.secret
        sender_wallet.__class__ = Secret.get_secret_wallet(self.network.symbol)

        receiver_wallet = account.accountsecret.get_crypto_wallet(self.network)

        fee_amount = self.get_asset_fee()

        base_asset = Asset.objects.get(symbol=self.network.symbol)
        trx_creator = TRXTransactionCreator(base_asset, sender_wallet)

        wallet = base_asset.get_wallet(fee_account)

        transfer = Transfer.objects.create(
            status=Transfer.NOT_BROADCAST,
            deposit=False,
            network=self.network,
            wallet=wallet,
            amount=fee_amount,
            out_address=receiver_wallet.address,
            deposit_address=self.network.get_deposit_address(wallet.account)
        )
        tx_id = trx_creator.from_transfer(transfer)

        transfer.trx_hash = tx_id
        transfer.status = Transfer.PENDING
        transfer.save()
