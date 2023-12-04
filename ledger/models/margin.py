from decimal import Decimal
from typing import Union
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from rest_framework import serializers

from accounts.models import Account
from ledger.exceptions import InsufficientBalance
from ledger.margin.margin_info import MarginInfo
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field, get_status_field, get_group_id_field, get_created_field, DONE, PENDING
from ledger.utils.price import get_last_price
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol


class MarginTransfer(models.Model):
    SPOT_TO_MARGIN = 'sm'
    MARGIN_TO_SPOT = 'ms'
    MARGIN_TO_POSITION = 'mp'
    POSITION_TO_MARGIN = 'pm'

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    amount = get_amount_field()

    type = models.CharField(
        max_length=2,
        choices=(
            (SPOT_TO_MARGIN, 'spot to margin'), (MARGIN_TO_SPOT, 'margin to spot'),
            (MARGIN_TO_POSITION, 'margin to position'), (POSITION_TO_MARGIN, 'position to margin')),
    )

    asset = models.ForeignKey(to=Asset, on_delete=models.PROTECT)
    position_symbol = models.ForeignKey(to=PairSymbol, null=True, blank=True, on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4)

    def save(self, *args, **kwargs):
        spot_wallet = self.asset.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = self.asset.get_wallet(self.account, Wallet.MARGIN)
        position_wallet = position = None

        if self.type in (self.MARGIN_TO_POSITION, self.POSITION_TO_MARGIN):
            if not self.position_symbol:
                raise ValueError('position_symbol is required')
            from ledger.models import MarginPosition
            position = MarginPosition.objects.filter(
                account=self.account,
                symbol=self.position_symbol,
                status=MarginPosition.OPEN
            ).first()
            if not position:
                raise ValueError('No open position found for this symbol')
            position_wallet = self.asset.get_wallet(self.account, Wallet.MARGIN, position.group_id)

        if self.type == self.SPOT_TO_MARGIN:
            sender, receiver = spot_wallet, margin_wallet

        elif self.type == self.MARGIN_TO_SPOT:
            sender, receiver = margin_wallet, spot_wallet

        elif self.type == self.MARGIN_TO_POSITION:
            sender, receiver = margin_wallet, position_wallet

            position.net_amount += self.amount
            position.save(update_fields=['net_amount'])

        elif self.type == self.POSITION_TO_MARGIN:
            sender, receiver = position_wallet, margin_wallet
            if not position.has_enough_margin(self.amount):
                raise InsufficientBalance

            position.net_amount -= self.amount
            position.save(update_fields=['net_amount'])
        else:
            raise NotImplementedError

        sender.has_balance(self.amount, raise_exception=True)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            super(MarginTransfer, self).save(*args)
            pipeline.new_trx(sender, receiver, self.amount, Trx.MARGIN_TRANSFER, self.group_id)
            if position:
                position.update_liquidation_price(pipeline, rebalance=False)


class MarginLoan(models.Model):
    BORROW, REPAY, OPEN = 'borrow', 'repay', 'open'

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    amount = get_amount_field()

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    type = models.CharField(
        max_length=8,
        choices=((BORROW, 'borrow'), (REPAY, 'repay')),
    )

    status = get_status_field()
    group_id = get_group_id_field()
    variant = get_group_id_field(null=True)

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_margin_loan_amount', ), ]

    @property
    def margin_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.MARGIN, self.variant)

    @property
    def loan_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.LOAN, self.variant)

    @classmethod
    def new_loan(cls, account: Account, asset: Asset, amount: Decimal, loan_type: str, pipeline: WalletPipeline,
                 variant=None):
        assert amount > 0
        assert asset.symbol != Asset.IRT
        assert loan_type in (cls.BORROW, cls.REPAY)

        loan = MarginLoan(
            account=account,
            asset=asset,
            variant=variant,
            amount=amount,
            type=loan_type,
            status=DONE
        )

        if loan_type == cls.REPAY:
            loan.loan_wallet.has_debt(-amount, raise_exception=True)
            loan.margin_wallet.has_balance(
                amount, raise_exception=True,
                pipeline_balance_diff=pipeline.get_wallet_free_balance_diff(loan.margin_wallet.id)
            )
        else:
            margin_info = MarginInfo.get(account)
            price = get_last_price(asset.symbol + Asset.USDT)

            # max_borrowable = margin_info.get_max_borrowable() / price

            # if amount > max_borrowable:
            #     raise MaxBorrowableExceeds()

        if loan_type == cls.BORROW:
            sender, receiver = loan.loan_wallet, loan.margin_wallet
        else:
            sender, receiver = loan.margin_wallet, loan.loan_wallet

        pipeline.new_trx(sender, receiver, amount, Trx.MARGIN_BORROW, loan.group_id)
        loan.save()

        return loan


class CloseRequest(models.Model):
    LIQUIDATION, USER, SYSTEM = 'liquid', 'user', 'system'

    created = get_created_field()
    group_id = get_group_id_field()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    margin_level = get_amount_field()

    reason = models.CharField(
        max_length=8, choices=[(LIQUIDATION, LIQUIDATION), (USER, USER), (SYSTEM, SYSTEM)]
    )

    status = get_status_field()

    class Meta:
        constraints = [
            CheckConstraint(check=Q(margin_level__gte=0), name='check_margin_level', ),
            UniqueConstraint(fields=['account'], condition=Q(status='pending'),
                             name='unique_margin_close_request_account'),
        ]

    @classmethod
    def is_liquidating(cls, account: Account) -> bool:
        return CloseRequest.objects.filter(account=account, status=PENDING).exists()

    @classmethod
    def close_margin(cls, account: Account, reason: str) -> Union['CloseRequest', None]:
        if cls.is_liquidating(account):
            return

        margin_info = MarginInfo.get(account)

        close_request = CloseRequest.objects.create(
            account=account,
            margin_level=margin_info.get_margin_level(),
            reason=reason,
            status=PENDING
        )

        from ledger.margin.closer import MarginCloser
        engine = MarginCloser(close_request, force_liquidation=reason == cls.LIQUIDATION)
        engine.start()

        close_request.status = DONE
        close_request.save()

        return close_request


class SymbolField(serializers.CharField):
    def to_representation(self, value: PairSymbol):
        if value:
            return value.name

    def to_internal_value(self, data: str):
        if not data:
            return
        else:
            return PairSymbol.get_by(name=data)
