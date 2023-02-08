import logging

from decouple import config
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords

from accounts.models import Account
from accounts.models import Notification
from accounts.tasks.send_sms import send_message_by_kavenegar
from accounts.utils import email
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from accounts.utils.validation import gregorian_to_jalali_datetime_str
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.fields import get_group_id_field
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class FiatWithdrawRequest(models.Model):
    history = HistoricalRecords()

    INIT, PROCESSING, PENDING, CANCELED, DONE = 'init', 'process', 'pending', 'canceled', 'done'

    MANUAL, ZIBAL, PAYIR, ZARINPAL, JIBIT = 'manual', 'zibal', 'payir', 'zarinpal', 'jibit'
    CHANEL_CHOICES = ((ZIBAL, ZIBAL), (PAYIR, PAYIR), (JIBIT, JIBIT), (MANUAL, MANUAL))

    FREEZE_TIME = 3 * 60

    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT, verbose_name='حساب بانکی')

    amount = models.PositiveIntegerField(verbose_name='میزان برداشت')
    fee_amount = models.PositiveIntegerField(verbose_name='کارمزد')

    status = models.CharField(
        default=INIT,
        max_length=10,
        choices=[(INIT, INIT), (PROCESSING, PROCESSING), (PENDING, PENDING), (DONE, DONE), (CANCELED, CANCELED)]
    )

    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')
    ref_doc = models.FileField(verbose_name='رسید انتقال', null=True, blank=True)

    comment = models.TextField(verbose_name='نظر', blank=True)

    withdraw_datetime = models.DateTimeField(null=True, blank=True)
    receive_datetime = models.DateTimeField(null=True, blank=True)

    withdraw_channel = models.CharField(max_length=10, choices=CHANEL_CHOICES, default=PAYIR)

    risks = models.JSONField(null=True, blank=True)

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
        assert self.status == self.PROCESSING

        if self.withdraw_channel == self.MANUAL:
            return

        if self.ref_id:
            self.status = self.PENDING
            self.save(update_fields=['status'])
            return

        from financial.utils.withdraw import ProviderError

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

        try:
            withdraw = self.channel_handler.create_withdraw(
                wallet_id,
                self.bank_account,
                self.amount,
                self.id
            )
            self.ref_id = withdraw.tracking_id
            self.withdraw_datetime = timezone.now()
            self.receive_datetime = withdraw.receive_datetime
            self.comment = withdraw.message

            self.save(update_fields=['ref_id', 'withdraw_datetime', 'receive_datetime', 'comment'])
            self.change_status(withdraw.status)

        except ProviderError as e:
            self.comment = str(e)
            self.save(update_fields=['comment'])

    def update_status(self):
        from financial.utils.withdraw import FiatWithdraw

        withdraw_handler = FiatWithdraw.get_withdraw_channel(self.withdraw_channel)
        withdraw_data = withdraw_handler.get_withdraw_status(self.id, self.ref_id)
        status = withdraw_data.status

        logger.info(f'FiatRequest {self.id} status: {status}')

        if status in (FiatWithdraw.DONE, FiatWithdraw.CANCELED):
            self.change_status(status)

        if not self.ref_id and withdraw_data.tracking_id:
            self.ref_id = withdraw_data.tracking_id
            self.save(update_fields=['ref_id'])

    def alert_withdraw_verify_status(self):
        user = self.bank_account.user

        if self.status == self.PENDING and self.withdraw_datetime:
            title = 'درخواست برداشت شما به بانک ارسال گردید.'
            description = 'وجه درخواستی شما در سیکل بعدی پایا {} به حساب شما واریز خواهد شد.'.format(
                gregorian_to_jalali_datetime_str(self.withdraw_datetime)
            )
            level = Notification.SUCCESS
            template = 'withdraw-accepted'
            email_template = email.SCOPE_SUCCESSFUL_FIAT_WITHDRAW

        elif self.status == self.CANCELED:
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
                'brand': settings.BRAND,
                'panel_url': settings.PANEL_URL,
                'logo_elastic_url': config('LOGO_ELASTIC_URL'),
            }
        )

    def change_status(self, new_status: str):
        with transaction.atomic():
            withdraw = FiatWithdrawRequest.objects.select_for_update().get(id=self.id)

            old_status = withdraw.status

            if old_status == new_status:
                return

            assert old_status not in (self.CANCELED, self.DONE)

            with WalletPipeline() as pipeline:  # type: WalletPipeline
                if new_status in (self.CANCELED, self.DONE):
                    pipeline.release_lock(withdraw.group_id)

                if (old_status, new_status) in (self.PROCESSING, self.PENDING):
                    withdraw.withdraw_datetime = timezone.now()
                elif new_status == self.DONE:
                    withdraw.build_trx(pipeline)

                withdraw.status = new_status
                withdraw.save(update_fields=['status'])

        self.alert_withdraw_verify_status()

    def clean(self):
        old = None
        if self.id:
            old = FiatWithdrawRequest.objects.get(id=self.id)

        if old and old.status in (FiatWithdrawRequest.DONE, FiatWithdrawRequest.CANCELED) and\
                self.status != old.status:
            raise ValidationError('امکان تغییر وضعیت برای این تراکنش وجود ندارد.')

        if old:
            old.change_status(self.status)

        # super().save_model(request, fiat_withdraw_request, form, change)

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'
