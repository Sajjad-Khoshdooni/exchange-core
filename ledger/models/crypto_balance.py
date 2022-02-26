from decimal import Decimal

from django.db import models

from ledger.crypto_account_balance_getter import CryptoAccountBalanceGetterFactory
from ledger.models import Transfer
from ledger.utils.fields import get_amount_field
from ledger.withdraw.withdraw_handler import WithdrawHandler


class CryptoBalance(models.Model):
    amount = get_amount_field(default=Decimal(0))
    deposit_address = models.ForeignKey('ledger.DepositAddress', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('deposit_address', 'asset')

    def update(self):
        balance = CryptoAccountBalanceGetterFactory.build(self.deposit_address.network).get_asset_of_account(
            self.deposit_address, self.asset
        )
        self.amount = balance
        self.save()

    def send_to(self, address: str, amount: Decimal):
        wallet = self.asset.get_wallet(self.deposit_address.account)

        transfer = Transfer.objects.create(
            source=Transfer.SELF,
            deposit=False,
            network=self.deposit_address.network,
            wallet=wallet,
            deposit_address=self.deposit_address,
            amount=amount,
            out_address=address,
            hidden=True
        )

        WithdrawHandler.withdraw_from_transfer(transfer)
