from uuid import uuid4

from django.db import models, transaction

from accounts.models import Account
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field
from ledger.utils.margin import get_margin_info, get_margin_level

TRANSFER_OUT_BLOCK_ML = 2
BORROW_BLOCK_ML = 1.5
MARGIN_CALL_ML_THRESHOLD = 1.35
LIQUIDATION_ML_THRESHOLD = 1.15


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

            margin_info = get_margin_info(self.account)

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

    amount = models.PositiveIntegerField()

    type = models.CharField(
        max_length=1,
        choices=((BORROW, 'borrow'), (REPAY, 'r')),
    )

    group_id = models.UUIDField(default=uuid4)

    def save(self, *args, **kwargs):
        asset = Asset.get(Asset.USDT)

        margin_wallet = asset.get_wallet(self.account, Wallet.MARGIN)
        borrow_wallet = asset.get_wallet(self.account, Wallet.BORROW)

        if self.type == self.REPAY:
            sender = borrow_wallet
            receiver = margin_wallet

        elif self.type == self.BORROW:
            sender = margin_wallet
            receiver = borrow_wallet

            margin_info = get_margin_info(self.account)

            future_total_borrow = margin_info.total_debt + self.amount
            future_margin_level = get_margin_level(margin_info.total_assets, future_total_borrow)

            if future_margin_level <= BORROW_BLOCK_ML:
                raise InsufficientBalance
        else:
            raise NotImplementedError

        with transaction.atomic():
            self.lock = sender.lock_balance(self.amount)
            super().save(*args, **kwargs)

        with transaction.atomic():
            Trx.transaction(sender, receiver, self.amount, Trx.MARGIN_TRANSFER)
            self.lock.release()
