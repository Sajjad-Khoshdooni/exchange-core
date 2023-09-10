import logging
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from simple_history.models import HistoricalRecords

from accounts.models import Account
from accounts.models import Notification
from accounts.tasks.send_sms import send_message_by_kavenegar
from accounts.utils import email
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_system_message
from accounts.utils.validation import gregorian_to_jalali_datetime_str
from analytics.event.producer import get_kafka_producer
from analytics.utils.dto import TransferEvent
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.external_price import get_external_price
from ledger.utils.fields import get_group_id_field
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class BaseTransfer(models.Model):
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    amount = models.PositiveIntegerField(verbose_name='میزان برداشت')
    gateway = models.ForeignKey('Gateway', on_delete=models.PROTECT)
    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT, verbose_name='حساب بانکی')
    group_id = get_group_id_field()
    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')

    class Meta:
        abstract = True


class FiatWithdrawRequest(BaseTransfer):
    history = HistoricalRecords()

    STATUSES = INIT, PROCESSING, PENDING, CANCELED, DONE, REFUND = \
        'init', 'process', 'pending', 'canceled', 'done', 'refund'

    FREEZE_TIME = 3 * 60

    fee_amount = models.PositiveIntegerField(verbose_name='کارمزد')

    status = models.CharField(
        default=INIT,
        max_length=10,
        choices=[
            (s, s) for s in STATUSES
        ]
    )

    comment = models.TextField(verbose_name='نظر', blank=True)

    withdraw_datetime = models.DateTimeField(null=True, blank=True)
    receive_datetime = models.DateTimeField(null=True, blank=True)

    risks = models.JSONField(null=True, blank=True)
    login_activity = models.ForeignKey('accounts.LoginActivity', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def total_amount(self):
        return self.amount + self.fee_amount

    def build_trx(self, pipeline: WalletPipeline):
        asset = Asset.get(Asset.IRT)
        out_wallet = asset.get_wallet(Account.out())

        account = self.bank_account.user.get_account()

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

        if self.ref_id:
            self.status = self.PENDING
            self.save(update_fields=['status'])
            return

        from financial.utils.withdraw import ProviderError
        from financial.utils.withdraw import FiatWithdraw

        api_handler = FiatWithdraw.get_withdraw_channel(self.gateway)

        try:
            withdraw = api_handler.create_withdraw(transfer=self)
            self.ref_id = withdraw.tracking_id
            self.withdraw_datetime = timezone.now()
            self.receive_datetime = withdraw.receive_datetime
            self.comment = withdraw.message

            self.save(update_fields=['ref_id', 'withdraw_datetime', 'receive_datetime', 'comment'])
            self.change_status(withdraw.status)

        except ProviderError as e:
            self.comment = str(e)
            self.save(update_fields=['comment'])

            send_system_message("Manual fiat withdraw", link=url_to_edit_object(self))

    def update_status(self):
        from financial.utils.withdraw import FiatWithdraw

        withdraw_handler = FiatWithdraw.get_withdraw_channel(self.gateway)
        withdraw_data = withdraw_handler.get_withdraw_status(self)
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
            }
        )

    def refund(self):
        assert self.status == self.DONE

        with WalletPipeline() as pipeline:
            for trx in Trx.objects.filter(group_id=self.group_id):
                trx.revert(pipeline)

            self.status = self.REFUND
            self.save(update_fields=['status'])

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

        if old and old.status in (FiatWithdrawRequest.DONE, FiatWithdrawRequest.CANCELED) and \
                self.status != old.status:
            raise ValidationError('امکان تغییر وضعیت برای این تراکنش وجود ندارد.')

        if old:
            old.change_status(self.status)

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'


@receiver(post_save, sender=FiatWithdrawRequest)
def handle_withdraw_request_save(sender, instance, created, **kwargs):
    if instance.status != FiatWithdrawRequest.DONE or settings.DEBUG_OR_TESTING_OR_STAGING:
        return

    usdt_price = get_external_price(coin='USDT', base_coin='IRT', side='buy')

    event = TransferEvent(
        id=instance.id,
        user_id=instance.bank_account.user_id,
        amount=instance.amount,
        coin='IRT',
        network='IRT',
        created=instance.created,
        value_irt=instance.amount,
        value_usdt=float(instance.amount) / float(usdt_price),
        is_deposit=False,
        event_id=uuid.uuid5(uuid.NAMESPACE_DNS, str(instance.id) + TransferEvent.type + 'fiat_withdraw')
    )

    get_kafka_producer().produce(event)
