from decimal import Decimal

from django.db import models

from accounts.models import User
from ledger.utils.price import get_trading_price_usdt


class Account(models.Model):
    SYSTEM = 's'
    OUT = 'o'
    ORDINARY = None

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    type = models.CharField(
        max_length=1,
        choices=((SYSTEM, 'system'), (OUT, 'out'), (ORDINARY, 'ordinary')),
        blank=True,
        null=True,
        unique=True
    )

    last_margin_warn = models.DateTimeField(null=True, blank=True)

    @classmethod
    def system(cls) -> 'Account':
        return Account.objects.get(type=cls.SYSTEM)

    @classmethod
    def out(cls) -> 'Account':
        return Account.objects.get(type=cls.OUT)

    def __str__(self):
        if self.type == self.SYSTEM:
            return 'system'
        elif self.type == self.OUT:
            return 'out'
        else:
            return str(self.user)

    def get_total_balance_usdt(self, market: str, side: str):
        from ledger.models import Wallet

        wallets = Wallet.objects.filter(account=self, market=market)

        total = Decimal('0')

        for wallet in wallets:
            balance = wallet.get_free()
            total += balance * get_trading_price_usdt(wallet.asset.symbol, side, raw_price=True)

        return total

    def save(self, *args, **kwargs):
        super(Account, self).save(*args, **kwargs)

        if self.type and self.user:
            raise Exception('User connected to system account')
