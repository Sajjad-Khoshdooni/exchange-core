from _helpers.blockchain.tron import get_tron_client
from accounts.models import Account
from ledger.models import Transfer, Network, Asset, CryptoBalance
from ledger.withdraw.transaction_creator import TransactionCreatorBuilder
from wallet.models import Secret

tron = get_tron_client()


class FeeHandler:
    BASE_ASSET = {
        'TRX': 'TRX',
        'BSC': 'BNB'
    }

    NETWORK_ASSET_FEE = {
        'TRX': {
            'TRX': 0,
            'USDT': 10
        },
        'BSC': {
            'BNB': 0.0001,
            'DEFAULT': 0.00015
        }
    }

    def __init__(self, network: Network, asset: Asset):
        self.network = network
        self.asset = asset

    def get_asset_fee(self):
        network_fees = self.NETWORK_ASSET_FEE.get(self.network.symbol, {})
        fee = network_fees.get(self.asset.symbol, None) or network_fees.get('DEFAULT', None)
        if fee is None:
            raise NotImplementedError
        return fee

    def is_balance_enough_for_fee(self, account: Account):
        balance, _ = CryptoBalance.objects.get_or_create(
            deposit_address=self.network.get_deposit_address(account),
            asset=Asset.objects.get(symbol=self.BASE_ASSET[self.network.symbol]),
        )
        balance.update()
        return balance.amount >= self.get_asset_fee()

    def supply_fee_for_asset(self, fee_account: Account, account: Account):
        if (
            self.network.symbol not in self.NETWORK_ASSET_FEE
        ):
            raise NotImplementedError
        sender_wallet = fee_account.accountsecret.secret
        sender_wallet.__class__ = Secret.get_secret_wallet(self.network.symbol)

        receiver_wallet = account.accountsecret.get_crypto_wallet(self.network)

        fee_amount = self.get_asset_fee()

        base_asset = Asset.objects.get(symbol=self.BASE_ASSET[self.network.symbol])

        trx_creator = TransactionCreatorBuilder(
            network=self.network,
            asset=base_asset,
            wallet=sender_wallet
        ).build()

        wallet = base_asset.get_wallet(fee_account)

        transfer = Transfer.objects.create(
            status=Transfer.PROCESSING,
            source=Transfer.SELF,
            deposit=False,
            network=self.network,
            wallet=wallet,
            amount=fee_amount,
            out_address=receiver_wallet.address,
            deposit_address=self.network.get_deposit_address(wallet.account),
            is_fee=True
        )
        tx_id = trx_creator.from_transfer(transfer)

        transfer.trx_hash = tx_id
        transfer.status = Transfer.PENDING
        transfer.save()
