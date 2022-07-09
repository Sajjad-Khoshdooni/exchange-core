from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Account
from ledger.models import DepositAddress


class Network(models.Model):
    ETH = 'ETH'
    TRX = 'TRX'
    BSC = 'BSC'

    symbol = models.CharField(max_length=16, unique=True, db_index=True)
    name = models.CharField(max_length=128, blank=True)

    can_withdraw = models.BooleanField(default=True)
    can_deposit = models.BooleanField(default=False)

    min_confirm = models.PositiveIntegerField(default=100, validators=[MinValueValidator(1)])
    unlock_confirm = models.PositiveIntegerField(default=0)

    explorer_link = models.CharField(max_length=128, blank=True)
    address_regex = models.CharField(max_length=128, blank=True)
    is_universal = models.BooleanField(default=False)

    need_memo = models.BooleanField(default=False)

    def get_deposit_address(self, account: Account) -> DepositAddress:
        return DepositAddress.new_deposit_address(account=account, network=self.symbol)

    def __str__(self):
        return self.symbol
