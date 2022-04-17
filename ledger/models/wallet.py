from decimal import Decimal

from django.db import models
from django.db.models import Sum

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, InsufficientDebt
from ledger.models import BalanceLock
from ledger.utils.price import BUY, SELL, get_trading_price_usdt, get_tether_irt_price


class Wallet(models.Model):
    SPOT, MARGIN, LOAN = 'spot', 'margin', 'loan'
    MARKETS = (SPOT, MARGIN, LOAN)
    MARKET_CHOICES = ((SPOT, SPOT), (MARGIN, MARGIN), (LOAN, LOAN))

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT, limit_choices_to={'enable': True})

    market = models.CharField(
        max_length=8,
        choices=MARKET_CHOICES,
    )

    def __str__(self):
        market_verbose = dict(self.MARKET_CHOICES)[self.market]
        return '%s Wallet %s [%s]' % (market_verbose, self.asset, self.account)

    class Meta:
        unique_together = [('account', 'asset', 'market')]

    def get_balance(self) -> Decimal:
        from ledger.models import Trx

        received = Trx.objects.filter(receiver=self).aggregate(amount=Sum('amount'))['amount'] or 0
        sent = Trx.objects.filter(sender=self).aggregate(amount=Sum('amount'))['amount'] or 0

        return received - sent

    def get_locked(self) -> Decimal:
        from ledger.models import BalanceLock
        return BalanceLock.objects.filter(wallet=self, freed=False).aggregate(amount=Sum('amount'))['amount'] or 0

    def lock_balance(self, amount: Decimal) -> BalanceLock:
        assert amount > 0

        if self.account.type != Account.SYSTEM:
            self.has_balance(amount, raise_exception=True)

        return BalanceLock.objects.create(wallet=self, amount=amount)

    def get_free(self) -> Decimal:
        return self.get_balance() - self.get_locked()

    def get_free_usdt(self) -> Decimal:
        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(SELL)
            return self.get_free() / tether_irt

        return self.get_free() * get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

    def get_free_irt(self):
        if self.asset.symbol == self.asset.IRT:
            return self.get_free()

        tether_irt = get_tether_irt_price(SELL)
        return self.get_free_usdt() * tether_irt

    def get_balance_usdt(self) -> Decimal:
        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(SELL)
            return self.get_balance() / tether_irt

        return self.get_balance() * get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

    def get_balance_irt(self):
        if self.asset.symbol == self.asset.IRT:
            return self.get_balance()

        tether_irt = get_tether_irt_price(SELL)
        return self.get_balance_usdt() * tether_irt

    def has_balance(self, amount: Decimal, raise_exception: bool = False) -> bool:
        if amount < 0:
            can = False
        else:
            can = self.get_free() >= amount

        if raise_exception and not can:
            raise InsufficientBalance()

        return can

    def has_debt(self, amount: Decimal, raise_exception: bool = False) -> bool:
        if amount > 0:
            can = False
        else:
            can = -self.get_free() >= -amount

        if raise_exception and not can:
            raise InsufficientDebt()

        return can
