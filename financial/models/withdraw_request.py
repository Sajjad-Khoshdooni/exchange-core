from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import Account
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.fields import get_status_field, DONE, get_group_id_field, get_lock_field


class FiatWithdrawRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT)

    amount = models.PositiveIntegerField()
    fee_amount = models.PositiveIntegerField()

    status = get_status_field()
    lock = get_lock_field()

    ref_id = models.CharField(max_length=128, blank=True)

    @property
    def total_amount(self):
        return self.amount + self.fee_amount

    def build_trx(self):
        asset = Asset.get(Asset.IRT)
        out_wallet = asset.get_wallet(Account.out())

        account = self.bank_account.user.account

        sender, receiver = asset.get_wallet(account), out_wallet

        Trx.transaction(
            group_id=self.group_id,
            sender=sender,
            receiver=receiver,
            amount=self.amount,
            scope=Trx.TRANSFER
        )

        if self.fee_amount:
            Trx.transaction(
                group_id=self.group_id,
                sender=sender,
                receiver=asset.get_wallet(Account.system()),
                amount=self.fee_amount,
                scope=Trx.COMMISSION
            )

    def clean(self):
        old = self.id and FiatWithdrawRequest.objects.get(id=self.id)

        if old and old.status == DONE and self.status != DONE:
            raise ValidationError('Cant change status')

        if self.status == DONE and not self.ref_id:
            raise ValidationError('ref_id cant be empty')

    def save(self, *args, **kwargs):
        old = self.id and FiatWithdrawRequest.objects.get(id=self.id)

        if old and old.status == DONE and self.status != DONE:
            return

        with transaction.atomic():
            super().save(*args, **kwargs)

            if (not old or old.status != DONE) and self.status == DONE:
                self.lock.release()
                self.build_trx()

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)
