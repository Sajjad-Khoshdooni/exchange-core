from decimal import Decimal

from django.db import models
from django.db.models import Sum

from ledger.exceptions import InsufficientBalance
from ledger.utils.fields import get_amount_field


class Wallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('account.Account', on_delete=models.PROTECT)
    balance = get_amount_field()
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)

    def get_balance(self) -> Decimal:
        from ledger.models import Trx

        received = Trx.objects.filter(receiver=self).aggregate(amount=Sum('amount'))['amount'] or 0
        sent = Trx.objects.filter(sender=self).aggregate(amount=Sum('amount'))['amount'] or 0

        return received - sent

    def can_buy(self, amount: Decimal, raise_exception: bool = False) -> bool:
        can = self.get_balance() >= amount

        if raise_exception and not can:
            raise InsufficientBalance()

        return can
