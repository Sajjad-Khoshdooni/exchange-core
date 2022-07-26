from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, F

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, InsufficientDebt
from ledger.utils.fields import get_amount_field
from ledger.utils.price import BUY, get_trading_price_usdt, get_tether_irt_price
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
    balance = get_amount_field(default=Decimal(0), validators=())
    locked = get_amount_field(default=Decimal(0))

    variant = models.UUIDField(editable=False, null=True, blank=True)

    def __str__(self):
        market_verbose = dict(self.MARKET_CHOICES)[self.market]
        return '%s Wallet %s [%s]' % (market_verbose, self.asset, self.account)

    class Meta:
        unique_together = [('account', 'asset', 'market', 'variant')]
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

    def get_free_usdt(self, side: str = BUY) -> Decimal:
        if self.get_free() == 0:
            return Decimal(0)

        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(side)
            return self.get_free() / tether_irt

        price = get_trading_price_usdt(self.asset.symbol, side, raw_price=True)

        if price:
            return self.get_free() * price

    def get_free_irt(self, side: str = BUY):
        if self.get_free() == 0:
            return Decimal(0)

        if self.asset.symbol == self.asset.IRT:
            return self.get_free()

        tether_irt = get_tether_irt_price(side)

        free_usdt = self.get_free_usdt()

        if free_usdt:
            return free_usdt * tether_irt

    def get_balance_usdt(self, side: str = BUY) -> Decimal:
        if self.balance == 0:
            return Decimal(0)

        if self.asset.symbol == self.asset.IRT:
            tether_irt = get_tether_irt_price(side)
            return self.get_balance() / tether_irt

        price = get_trading_price_usdt(self.asset.symbol, side, raw_price=True)

        if price is not None:
            return self.get_balance() * price

    def get_balance_irt(self, side: str = BUY):
        if self.balance == 0:
            return Decimal(0)

        if self.asset.symbol == self.asset.IRT:
            return self.get_balance()

        tether_irt = get_tether_irt_price(side)
        balance_usdt = self.get_balance_usdt()

        if balance_usdt is not None:
            return balance_usdt * tether_irt

    def has_balance(self, amount: Decimal, raise_exception: bool = False) -> bool:
        assert amount >= 0 and self.market != Wallet.LOAN

        if not self.check_balance:
            can = True
        else:
            can = self.get_free() >= amount

        if raise_exception and not can:
            raise InsufficientBalance()

        return can

    def has_debt(self, amount: Decimal, raise_exception: bool = False) -> bool:
        assert amount <= 0 and self.market == Wallet.LOAN

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

    def reserve_funds(self, amount: Decimal):
        assert self.market in (Wallet.SPOT, Wallet.MARGIN)
        assert self.variant is None  # means its not reserved wallet

        from ledger.models import Trx

        if self.has_balance(amount, raise_exception=True):
            group_id = uuid4()
            with WalletPipeline() as pipeline:
                child_wallet = Wallet.objects.create(
                    account=self.account,
                    asset=self.asset,
                    market=self.market,
                    variant=group_id,
                )
                pipeline.new_trx(
                    sender=self,
                    receiver=child_wallet,
                    amount=amount,
                    group_id=group_id,
                    scope=Trx.RESERVE
                )
                ReserveWallet.objects.create(
                    sender=self,
                    receiver=child_wallet,
                    amount=amount,
                    group_id=group_id
                )
                return group_id


class ReserveWallet(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='reserve_wallet')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='reserved_wallet')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    refund_completed = models.BooleanField(default=False)

    def refund(self):
        if self.refund_completed:
            raise Exception('Cannot refund already refunded wallet')
        with WalletPipeline() as pipeline:
            from ledger.models import Trx
            pipeline.new_trx(
                sender=self,
                receiver=self.sender,
                amount=self.receiver.balance,
                group_id=self.group_id,
                scope=Trx.RESERVE
            )
            self.refund_completed = True
            self.save(update_fields=['refund_completed'])
            return True

    class Meta:
        unique_together = ('group_id', 'sender', 'receiver')

    def save(self, *args, **kwargs):
        assert self.sender.asset == self.receiver.asset
        assert self.sender != self.receiver
        assert self.amount > 0

        return super(ReserveWallet, self).save(*args, **kwargs)
