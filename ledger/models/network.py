from django.core.validators import MinValueValidator
from django.db import models

from accounts.models import Account


class Network(models.Model):
    ETH = 'ETH'
    TRX = 'TRX'

    symbol = models.CharField(max_length=8, unique=True, db_index=True)
    schema = models.ForeignKey(to='ledger.AddressSchema', on_delete=models.PROTECT)

    can_withdraw = models.BooleanField(default=True)
    can_deposit = models.BooleanField(default=False)

    minimum_block_to_confirm = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])

    def get_deposit_address(self, account: Account) -> str:
        from ledger.models import DepositAddress

        deposit_address, _ = DepositAddress.objects.get_or_create(account=account, schema=self.schema)
        return deposit_address.address

    def __str__(self):
        return self.symbol
