import logging

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from yekta_config.config import config

from accounts.models import Account
from accounts.models import Notification
from accounts.tasks.send_sms import send_message_by_kavenegar
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from financial.models import BankAccount
from financial.utils.pay_ir import Payir
from ledger.models import Trx, Asset
from ledger.utils.fields import DONE, get_group_id_field, get_lock_field, PENDING, CANCELED
from ledger.utils.precision import humanize_number

logger = logging.getLogger(__name__)


class FiatWithdrawRequest(models.Model):
    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'

    FREEZE_TIME = 3 * 60

    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT, verbose_name='حساب بانکی')

    amount = models.PositiveIntegerField(verbose_name='میزان برداشت')
    fee_amount = models.PositiveIntegerField(verbose_name='کارمزد')

    status = models.CharField(
        default=PROCESSING,
        max_length=10,
        choices=[(PROCESSING, 'در حال پردازش'), (PENDING, 'در انتظار'), (DONE, 'انجام شده'), (CANCELED, 'لغو شده')]
    )
    lock = get_lock_field()

    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')
    ref_doc = models.FileField(verbose_name='رسید انتقال', null=True, blank=True)

    comment = models.TextField(verbose_name='نظر', blank=True)

    done_datetime = models.DateTimeField(null=True, blank=True)

    provider_withdraw_id = models.CharField(max_length=64, blank=True)

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

        if old and old_status != PENDING and self.status != old_status:
            raise ValidationError('امکان تغییر وضعیت وجود ندارد.')

        if self.status == DONE and not self.ref_id:
            raise ValidationError('شماره پیگیری خالی است.')

        if self.status == DONE and not self.ref_id:
            raise ValidationError('رسید انتقال خالی است.')

    def create_withdraw_request_paydotir(self):
        assert not self.provider_withdraw_id
        assert self.status == self.PROCESSING

        wallet_id = config('PAY_IR_WALLET_ID', cast=int)
        wallet = Payir.get_wallet_data(wallet_id)

        if wallet.free < self.amount:
            logger.info(f'Not enough wallet balance to full fill bank acc')

            link = url_to_edit_object(self)
            send_support_message(
                message='موجودی هیچ یک از کیف پول‌ها برای انجام این تراکنش کافی نیست.',
                link=link
            )
            return

        self.provider_withdraw_id = Payir.withdraw(wallet_id, self.bank_account, self.amount, self.id)
        self.status = FiatWithdrawRequest.PENDING
        self.save()

    def update_status(self):
        if self.status != self.PENDING:
            return

        status = Payir.get_withdraw_status(self.id)

        logger.info(f'FiatRequest {self.id} status: {status}')

        if status == 4:
            self.status = DONE
            self.save()

        elif status in (5, 3):
            self.status = CANCELED
            self.save()

    def alert_withdraw_verify_status(self, old):
        if (not old or old.status != DONE) and self.status == DONE:
            title = 'درخواست برداشت شما با موفقیت انجام شد.'
            level = Notification.SUCCESS
            template = 'withdraw-accepted'

        elif (not old or old.status != CANCELED) and self.status == CANCELED:
            title = 'درخواست برداشت شما انجام نشد.'
            level = Notification.ERROR
            template = 'withdraw-rejected'
        else:
            return

        Notification.send(
            recipient=self.bank_account.user,
            title=title,
            level=level
        )
        send_message_by_kavenegar(
            phone=self.bank_account.user.phone,
            template=template,
            token=humanize_number(self.amount)
        )

    def save(self, *args, **kwargs):
        old = self.id and FiatWithdrawRequest.objects.get(id=self.id)

        with transaction.atomic():
            if self.status == DONE:
                self.done_datetime = timezone.now()

            super().save(*args, **kwargs)

            if (not old or old.status != DONE) and self.status == DONE:
                self.build_trx()

            if self.status in (self.CANCELED, self.DONE):
                self.lock.release()

        self.alert_withdraw_verify_status(old)

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'
