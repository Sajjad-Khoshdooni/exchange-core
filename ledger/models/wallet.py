from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, F

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, InsufficientDebt
from ledger.utils.fields import get_amount_field
from ledger.utils.price import BUY, SELL, get_trading_price_usdt, get_tether_irt_price
from ledger.utils.wallet_pipeline import WalletPipeline


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

    check_balance = models.BooleanField(default=True)
    balance = get_amount_field(default=Decimal(0))
    locked = get_amount_field(default=Decimal(0))

    def __str__(self):
        market_verbose = dict(self.MARKET_CHOICES)[self.market]
        return '%s Wallet %s [%s]' % (market_verbose, self.asset, self.account)

    class Meta:
        unique_together = [('account', 'asset', 'market')]
        constraints = [
            CheckConstraint(
                check=Q(check_balance=False) | (~Q(market='loan') & Q(balance__gte=0) & Q(balance__gte=F('locked'))) |
                      (Q(market='loan') & Q(balance__lte=0) & Q(locked=0)),
                name='valid_balance_constraint'
            ),
            CheckConstraint(
                check=Q(locked__gte=0),
                name='valid_locked_constraint'
            ),
        ]

    def get_balance(self) -> Decimal:
        return self.balance

    def get_locked(self) -> Decimal:
        return self.locked

    def get_free(self) -> Decimal:
        return self.balance - self.locked

    def get_free_usdt(self) -> Decimal:
        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(SELL)
            return self.get_free() / tether_irt

        price = get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

        if price:
            return self.get_free() * price

    def get_free_irt(self):
        if self.asset.symbol == self.asset.IRT:
            return self.get_free()

        tether_irt = get_tether_irt_price(SELL)

        free_usdt = self.get_free_usdt()

        if free_usdt:
            return free_usdt * tether_irt

    def get_balance_usdt(self) -> Decimal:
        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(SELL)
            return self.get_balance() / tether_irt

        price = get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

        if price:
            return self.get_balance() * price

    def get_balance_irt(self):
        if self.asset.symbol == self.asset.IRT:
            return self.get_balance()

        tether_irt = get_tether_irt_price(SELL)
        balance_usdt = self.get_balance_usdt()

        if balance_usdt:
            return balance_usdt * tether_irt

    def has_balance(self, amount: Decimal, raise_exception: bool = False) -> bool:
        if not self.check_balance:
            can = True
        elif amount < 0:
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

    def airdrop(self, amount: Decimal):
        assert settings.DEBUG_OR_TESTING

        from ledger.models import Trx
        from uuid import uuid4

        with WalletPipeline() as pipeline:
            pipeline.new_trx(
                sender=self.asset.get_wallet(Account.out()),
                receiver=self,
                amount=amount,
                group_id=uuid4(),
                scope=Trx.AIRDROP
            )

    def seize_funds(self, amount: Decimal = None):
        from ledger.models import Trx
        from uuid import uuid4

        with WalletPipeline() as pipeline:

            pipeline.new_trx(
                sender=self,
                receiver=self.asset.get_wallet(Account.system()),
                amount=amount or self.balance,
                group_id=uuid4(),
                scope=Trx.SEIZE
            )
