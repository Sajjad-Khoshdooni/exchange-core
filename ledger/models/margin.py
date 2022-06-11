from decimal import Decimal
from uuid import uuid4

from django.db import models, transaction

from accounts.models import Account
from ledger.exceptions import InsufficientBalance, MaxBorrowableExceeds
from ledger.models import Asset, Wallet, Trx
from ledger.utils.fields import get_amount_field, get_status_field, get_group_id_field, get_lock_field, DONE, \
    get_created_field
from ledger.utils.margin import MarginInfo
from ledger.utils.price import BUY, SELL, get_trading_price_usdt
from provider.models import ProviderOrder


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

        with transaction.atomic():
            super(MarginTransfer, self).save(*args)
            Trx.transaction(sender, receiver, self.amount, Trx.MARGIN_TRANSFER, self.group_id)


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
    lock = get_lock_field()
    group_id = get_group_id_field()

    @property
    def margin_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.MARGIN)

    @property
    def borrow_wallet(self) -> 'Wallet':
        return self.asset.get_wallet(self.account, Wallet.LOAN)

    def finalize(self):
        hedged = ProviderOrder.try_hedge_for_new_order(
            asset=self.asset,
            side=BUY if self.type == self.BORROW else SELL,
            amount=self.amount,
            scope=ProviderOrder.BORROW
        )

        if hedged:
            if self.type == self.BORROW:
                sender, receiver = self.borrow_wallet, self.margin_wallet
            else:
                sender, receiver = self.margin_wallet, self.borrow_wallet

            with transaction.atomic():
                self.status = DONE
                self.save()
                if self.lock:
                    self.lock.release()

                Trx.transaction(sender, receiver, self.amount, Trx.MARGIN_BORROW, self.group_id)

    @classmethod
    def new_loan(cls, account: Account, asset: Asset, amount: Decimal, loan_type: str):
        assert amount > 0
        assert asset.symbol != Asset.IRT

        with transaction.atomic():
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
                max_borrowable = margin_info.get_max_borrowable() / get_trading_price_usdt(asset.symbol, SELL, raw_price=True)

                if amount > max_borrowable:
                    raise MaxBorrowableExceeds()

                loan.save()

            loan.finalize()

            return loan


class MarginLiquidation(models.Model):
    created = get_created_field()
    group_id = get_group_id_field()

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    margin_level = get_amount_field()
