from django.core.exceptions import ValidationError
from django.db import models, transaction

from accounts.models import Account
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.fields import get_status_field, DONE, get_group_id_field, get_lock_field, PENDING


class FiatWithdrawRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT)

    amount = models.PositiveIntegerField()
    fee_amount = models.PositiveIntegerField()

    status = get_status_field()
    lock = get_lock_field()

    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')
    ref_doc = models.FileField(verbose_name='رسید انتقال', null=True, blank=True)

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
        old_status = old and old.status

        if old and old_status != PENDING and self.status == old_status:
            raise ValidationError('امکان تغییر وضعیت وجود ندارد.')

        if self.status == DONE and not self.ref_id:
            raise ValidationError('شماره پیگیری خالی است.')

        if self.status == DONE and not self.ref_id:
            raise ValidationError('رسید انتقال خالی است.')

    def save(self, *args, **kwargs):
        old = self.id and FiatWithdrawRequest.objects.get(id=self.id)
        old_status = old and old.status

        if old and old_status != PENDING and self.status != old_status:
            return

        with transaction.atomic():
            super().save(*args, **kwargs)

            if (not old or old.status != DONE) and self.status == DONE:
                self.build_trx()

            if self.status != PENDING:
                self.lock.release()

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'
