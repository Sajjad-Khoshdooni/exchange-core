from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Account
from ledger.models import DepositAddress, AccountSecret


class Network(models.Model):
    ETH = 'ETH'
    TRX = 'TRX'

    symbol = models.CharField(max_length=8, unique=True, db_index=True)

    can_withdraw = models.BooleanField(default=True)
    can_deposit = models.BooleanField(default=False)

    minimum_block_to_confirm = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])

    explorer_link = models.CharField(max_length=128, blank=True)

    def get_deposit_address(self, account: Account) -> DepositAddress:
        account_secret, _ = AccountSecret.objects.get_or_create(account=account)

        try:
            return DepositAddress.objects.get(network=self, account_secret=account_secret)
        except DepositAddress.DoesNotExist:
            return DepositAddress.new_deposit_address(account=account, network=self)

    def __str__(self):
        return self.symbol
