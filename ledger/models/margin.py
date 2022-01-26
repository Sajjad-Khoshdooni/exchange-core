from decimal import Decimal
from uuid import uuid4

from django.db import models, transaction

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, MaxBorrowableExceeds
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field, get_status_field, get_group_id_field, get_lock_field
from ledger.utils.margin import MarginInfo, get_margin_level, TRANSFER_OUT_BLOCK_ML


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

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE)

    group_id = models.UUIDField(default=uuid4)

    def save(self, *args, **kwargs):
        asset = Asset.get(Asset.USDT)

        spot_wallet = asset.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = asset.get_wallet(self.account, Wallet.MARGIN)

        if self.type == self.SPOT_TO_MARGIN:
            sender = spot_wallet
            receiver = margin_wallet

        elif self.type == self.MARGIN_TO_SPOT:
            sender = margin_wallet
            receiver = spot_wallet

            margin_info = MarginInfo.get(self.account)

            future_total_assets = margin_info.total_assets - self.amount
            future_margin_level = get_margin_level(future_total_assets, margin_info.total_debt)

            if future_margin_level <= TRANSFER_OUT_BLOCK_ML:
                raise InsufficientBalance
        else:
            raise NotImplementedError

        with transaction.atomic():
            self.lock = sender.lock_balance(self.amount)
            super(MarginTransfer, self).save(*args, **kwargs)

        with transaction.atomic():
            Trx.transaction(sender, receiver, self.amount, Trx.MARGIN_TRANSFER)
            self.lock.release()


class MarginLoan(models.Model):

    BORROW, REPAY = 'b', 'r'

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    amount = get_amount_field()

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    type = models.CharField(
        max_length=1,
        choices=((BORROW, 'borrow'), (REPAY, 'repay')),
    )

    status = get_status_field()
    lock = get_lock_field()
    group_id = get_group_id_field()

    @property
    def margin_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.MARGIN)

    @property
    def borrow_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.BORROW)

    # def create_ledger(self):
    #     if self.type == self.REPAY:
    #         sender
    #
    #     with transaction.atomic():
    #         Trx.transaction(self.margin_wallet, self.borrow_wallet, self.amount, Trx.MARGIN_BORROW)
    #         self.lock.release()

    def finalize(self):
        if self.type == self.REPAY:
            Trx.transaction(self.margin_wallet, self.borrow_wallet, self.amount, Trx.MARGIN_BORROW)
            lock.release()

    @classmethod
    def new_loan(cls, account: Account, asset: Asset, amount: Decimal, loan_type: str):
        tether = Asset.get(Asset.USDT)

        loan = MarginLoan(
            account=account,
            asset=asset,
            amount=amount,
            type=loan_type
        )

        if loan_type == cls.REPAY:
            loan.borrow_wallet.has_debt(-amount, raise_exception=True)
            loan.lock = loan.margin_wallet.lock_balance(amount)
            loan.save()

        else:
            margin_info = MarginInfo.get(account)
            max_borrowable = margin_info.get_max_borrowable()

            if amount > max_borrowable:
                raise MaxBorrowableExceeds()

            future_total_borrow = margin_info.total_debt + self.amount
            future_margin_level = get_margin_level(margin_info.total_assets, future_total_borrow)

            if future_margin_level <= BORROW_BLOCK_ML:
                raise InsufficientBalance
        else:
            raise NotImplementedError

        self.save()

        with transaction.atomic():
            self.lock = sender.lock_balance(self.amount)
            super().save(*args, **kwargs)

        with transaction.atomic():
            Trx.transaction(sender, receiver, self.amount, Trx.MARGIN_BORROW)
            self.lock.release()
