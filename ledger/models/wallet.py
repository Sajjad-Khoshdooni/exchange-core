from decimal import Decimal

from django.db import models
from django.db.models import Sum

from ledger.exceptions import InsufficientBalance


class Wallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)

    def __str__(self):
        return 'Wallet %s [%s]' % (self.asset, self.account)

    class Meta:
        unique_together = [('account', 'asset')]

    def get_balance(self) -> Decimal:
        from ledger.models import Trx

        received = Trx.objects.filter(receiver=self).aggregate(amount=Sum('amount'))['amount'] or 0
        sent = Trx.objects.filter(sender=self).aggregate(amount=Sum('amount'))['amount'] or 0

        return received - sent

    def get_locked(self) -> Decimal:
        from ledger.models import BalanceLock
        return BalanceLock.objects.filter(wallet=self, freed=False).aggregate(amount=Sum('amount'))['amount'] or 0

    def get_free(self) -> Decimal:
        return self.get_balance() - self.get_locked()

    def get_balance_usdt(self) -> Decimal:
        from ledger.utils.price import get_tether_irt_price, get_price

        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price()
            return self.get_balance() / tether_irt

        return self.get_balance() * get_price(self.asset.symbol)

    def get_balance_irt(self):
        if self.asset.symbol == self.asset.IRT:
            return self.get_balance()

        from ledger.utils.price import get_tether_irt_price
        tether_irt = get_tether_irt_price()
        return self.get_balance_usdt() * tether_irt

    def can_buy(self, amount: Decimal, raise_exception: bool = False) -> bool:
        can = self.get_free() >= amount

        if raise_exception and not can:
            raise InsufficientBalance()

        return can
