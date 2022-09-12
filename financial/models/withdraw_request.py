import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from yekta_config.config import config

from accounts.models import Account
from accounts.models import Notification
from accounts.tasks.send_sms import send_message_by_kavenegar
from accounts.utils import email
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from accounts.utils.validation import gregorian_to_jalali_datetime_str
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.fields import DONE, get_group_id_field, PENDING, CANCELED
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class FiatWithdrawRequest(models.Model):
    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'

    ZIBAL, PAYIR, ZARINPAL = 'zibal', 'payir', 'zarinpal'
    CHANEL_CHOICES = ((ZIBAL, ZIBAL), (PAYIR, PAYIR))

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

    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')
    ref_doc = models.FileField(verbose_name='رسید انتقال', null=True, blank=True)

    comment = models.TextField(verbose_name='نظر', blank=True)

    withdraw_datetime = models.DateTimeField(null=True, blank=True)
    receive_datetime = models.DateTimeField(null=True, blank=True)
    provider_withdraw_id = models.CharField(max_length=64, blank=True)

    withdraw_channel = models.CharField(max_length=10, choices=CHANEL_CHOICES, default=PAYIR)

    @property
    def total_amount(self):
        return self.amount + self.fee_amount

    @property
    def channel_handler(self):
        from financial.utils.withdraw import FiatWithdraw

        return FiatWithdraw.get_withdraw_channel(self.withdraw_channel)

    def build_trx(self, pipeline: WalletPipeline):
        asset = Asset.get(Asset.IRT)
        out_wallet = asset.get_wallet(Account.out())

        account = self.bank_account.user.account

        sender, receiver = asset.get_wallet(account), out_wallet

        pipeline.new_trx(
            group_id=self.group_id,
            sender=sender,
            receiver=receiver,
            amount=self.amount,
            scope=Trx.TRANSFER
        )

        if self.fee_amount:
            pipeline.new_trx(
                group_id=self.group_id,
                sender=sender,
                receiver=asset.get_wallet(Account.system()),
                amount=self.fee_amount,
                scope=Trx.COMMISSION
            )

    def create_withdraw_request(self):
        assert not self.provider_withdraw_id
        assert self.status == self.PROCESSING

        wallet_id = self.channel_handler.get_wallet_id()

        wallet = self.channel_handler.get_wallet_data(wallet_id)

        if wallet.free < self.amount:
            logger.info(f'Not enough wallet balance to full fill bank acc')

            link = url_to_edit_object(self)
            send_support_message(
                message='موجودی هیچ یک از کیف پول‌ها برای انجام این تراکنش کافی نیست.',
                link=link
            )
            return

        withdraw = self.channel_handler.create_withdraw(
            wallet_id,
            self.bank_account,
            self.amount,
            self.id
        )
        self.provider_withdraw_id = self.ref_id = withdraw.tracking_id
        self.change_status(withdraw.status)
        self.withdraw_datetime = timezone.now()
        self.receive_datetime = withdraw.receive_datetime

        self.save()

    def update_status(self):
        from financial.utils.withdraw import FiatWithdraw

        withdraw_handler = FiatWithdraw.get_withdraw_channel(self.withdraw_channel)
        status = withdraw_handler.get_withdraw_status(self.id, self.provider_withdraw_id)

        logger.info(f'FiatRequest {self.id} status: {status}')

        if status == FiatWithdraw.DONE:
            self.change_status(FiatWithdrawRequest.DONE)

        elif status == FiatWithdraw.CANCELED:
            self.change_status(FiatWithdrawRequest.CANCELED)

    def alert_withdraw_verify_status(self):
        user = self.bank_account.user

        if self.status == PENDING and self.withdraw_datetime:
            title = 'درخواست برداشت شما به بانک ارسال گردید.'
            description = 'وجه درخواستی شما در سیکل بعدی پایا {} به حساب شما واریز خواهد شد.'.format(
                gregorian_to_jalali_datetime_str(self.withdraw_datetime)
            )
            level = Notification.SUCCESS
            template = 'withdraw-accepted'
            email_template = email.SCOPE_SUCCESSFUL_FIAT_WITHDRAW

        elif self.status == CANCELED:
            title = 'درخواست برداشت شما لغو شد.'
            description = ''
            level = Notification.ERROR
            template = 'withdraw-rejected'
            email_template = email.SCOPE_CANCEL_FIAT_WITHDRAW
        else:
            return

        Notification.send(
            recipient=user,
            title=title,
            message=description,
            level=level,
        )
        send_message_by_kavenegar(
            phone=user.phone,
            template=template,
            token=humanize_number(self.amount)
        )

        email.send_email_by_template(
            recipient=user.email,
            template=email_template,
            context={
                'estimated_receive_time': self.receive_datetime or None,
                'brand': config('BRAND'),
                'panel_url': config('PANEL_URL'),
                'logo_elastic_url': config('LOGO_ELASTIC_URL'),
            }
        )

    def change_status(self, new_status: str):
        if self.status == new_status:
            return

        assert self.status not in (CANCELED, self.DONE)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            if new_status in (self.CANCELED, self.DONE):
                pipeline.release_lock(self.group_id)

            if new_status == DONE:
                self.build_trx(pipeline)

            if new_status == self.PENDING:
                self.withdraw_datetime = timezone.now()

            self.status = new_status
            self.save()

        self.alert_withdraw_verify_status()

    def clean(self):

        old = self.id and FiatWithdrawRequest.objects.get(id=self.id)

        if old and old.status in (FiatWithdrawRequest.DONE, FiatWithdrawRequest.CANCELED) and\
                self.status != old.status:
            raise ValidationError('امکان تغییر وضعیت برای این ترکانش وجود ندارد.')

        if old:
            old.change_status(self.status)

        # super().save_model(request, fiat_withdraw_request, form, change)

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'
