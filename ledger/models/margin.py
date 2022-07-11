from decimal import Decimal
from typing import Union
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, MaxBorrowableExceeds
from ledger.margin.margin_info import MarginInfo
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field, get_status_field, get_group_id_field, get_created_field, DONE, PENDING
from ledger.utils.price import SELL, get_trading_price_usdt
from ledger.utils.wallet_pipeline import WalletPipeline



class MarginTransfer(models.Model):
    SPOT_TO_MARGIN = 'sm'
    MARGIN_TO_SPOT = 'ms'

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    amount = models.PositiveIntegerField()

    type = models.CharField(
        max_length=2,
        choices=((SPOT_TO_MARGIN, 'spot to margin'), (MARGIN_TO_SPOT, 'margin to spot')),
    )

    asset = models.ForeignKey(to=Asset, on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4)

    def save(self, *args, **kwargs):
        spot_wallet = self.asset.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = self.asset.get_wallet(self.account, Wallet.MARGIN)

        if self.type == self.SPOT_TO_MARGIN:
            sender, receiver = spot_wallet, margin_wallet

        elif self.type == self.MARGIN_TO_SPOT:
            sender, receiver = margin_wallet, spot_wallet

            margin_info = MarginInfo.get(self.account)

            if self.amount > margin_info.get_max_transferable():
                raise InsufficientBalance
        else:
            raise NotImplementedError

        sender.has_balance(self.amount, raise_exception=True)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            super(MarginTransfer, self).save(*args)
            pipeline.new_trx(sender, receiver, self.amount, Trx.MARGIN_TRANSFER, self.group_id)


class MarginLoan(models.Model):
    BORROW, REPAY = 'borrow', 'repay'

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

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_margin_loan_amount', ), ]

    @property
    def margin_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.MARGIN)

    @property
    def loan_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.LOAN)

    @classmethod
    def new_loan(cls, account: Account, asset: Asset, amount: Decimal, loan_type: str):
        assert amount > 0
        assert asset.symbol != Asset.IRT
        assert loan_type in (cls.BORROW, cls.REPAY)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            loan = MarginLoan(
                account=account,
                asset=asset,
                amount=amount,
                type=loan_type,
                status=DONE
            )

            if loan_type == cls.REPAY:
                loan.loan_wallet.has_debt(-amount, raise_exception=True)
                loan.margin_wallet.has_balance(amount, raise_exception=True)
            else:
                margin_info = MarginInfo.get(account)
                max_borrowable = margin_info.get_max_borrowable() / get_trading_price_usdt(asset.symbol, SELL, raw_price=True)

                if amount > max_borrowable:
                    raise MaxBorrowableExceeds()

            if loan_type == cls.BORROW:
                sender, receiver = loan.loan_wallet, loan.margin_wallet
            else:
                sender, receiver = loan.margin_wallet, loan.loan_wallet

            pipeline.new_trx(sender, receiver, amount, Trx.MARGIN_BORROW, loan.group_id)

            loan.save()

            return loan


class CloseRequest(models.Model):
    LIQUIDATION, USER = 'liquid', 'user'

    created = get_created_field()
    group_id = get_group_id_field()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    margin_level = get_amount_field()

    reason = models.CharField(
        max_length=8, choices=[(LIQUIDATION, LIQUIDATION), (USER, USER)]
    )

    status = get_status_field()

    class Meta:
        constraints = [
            CheckConstraint(check=Q(margin_level__gte=0), name='check_margin_level', ),
            UniqueConstraint(fields=['account'], condition=Q(status='pending'), name='unique_margin_close_request_account'),
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
