from decimal import Decimal

from django.db import models

from ledger.crypto_account_balance_getter import CryptoAccountBalanceGetterFactory
from ledger.utils.fields import get_amount_field


class CryptoBalance(models.Model):
    amount = get_amount_field(default=Decimal(0))
    deposit_address = models.ForeignKey('ledger.DepositAddress', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('deposit_address', 'asset')

    def update(self):
        balance = CryptoAccountBalanceGetterFactory.build(self.deposit_address.network).get_asset_balance_of_account(
            self.deposit_address, self.asset
        )
        self.amount = balance
        self.save()


