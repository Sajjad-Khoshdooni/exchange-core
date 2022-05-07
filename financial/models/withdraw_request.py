from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from yekta_config import secret

from accounts.models import Notification
from accounts.models import Account
from financial.models import BankAccount
from ledger.models import Trx, Asset
from ledger.utils.fields import get_status_field, DONE, get_group_id_field, get_lock_field, PENDING, CANCELED
from accounts.tasks.send_sms import send_message_by_kavenegar
from ledger.utils.precision import humanize_number
import requests
import logging
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message

logger = logging.getLogger(__name__)


class FiatWithdrawRequest(models.Model):

    INIT, SENT, DONE, CANCELED = 'init', 'sent', 'done', 'canceled'

    BASE_URL = 'https://pay.ir'

    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    bank_account = models.ForeignKey(to=BankAccount, on_delete=models.PROTECT, verbose_name='حساب بانکی')

    amount = models.PositiveIntegerField(verbose_name='میزان برداشت')
    fee_amount = models.PositiveIntegerField(verbose_name='کارمزد')

    status = get_status_field()
    provider_request_status = models.CharField(
        default=INIT,
        max_length=10,
        choices=[(INIT, 'مرحله اولیه'), (SENT, 'ارسال شده'), (DONE, 'انجام شده'), (CANCELED, 'لغو شده')]
    )
    lock = get_lock_field()

    ref_id = models.CharField(max_length=128, blank=True, verbose_name='شماره پیگیری')
    ref_doc = models.FileField(verbose_name='رسید انتقال', null=True, blank=True)

    comment = models.TextField(verbose_name='نظر', blank=True)

    done_datetime = models.DateTimeField(null=True, blank=True)

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

    def get_available_wallet_id(self):

        resp = requests.get(
            self.BASE_URL + '/api/v2/wallets',
            headers={'Authorization': '%s' % secret('PAYDOTIR_WITHDRAW_KEY')}
        )
        resp = resp.json()
        if resp['success']:
            wallet_id = None
            for wallet in resp['data']['wallet']:
                if wallet['cashoutableAmount'] >= self.amount * 10:
                    wallet_id = wallet['id']
            return wallet_id
        else:
            raise Exception('fail in get wallet')

    def create_withdraw_request_paydotir(self):

        wallet_id = self.get_available_wallet_id()

        if wallet_id is None:
            self.status = CANCELED
            self.save()
            link = url_to_edit_object(self)
            send_support_message(
                message='موجودی هیچ یک از کیف پول‌ها برای انجام این تراکنش کافی نیست.',
                link=link
            )

        else:
            second_resp = requests.post(
                self.BASE_URL + '/api/v2/cashouts',
                headers={'Authorization': '%s' % secret('PAYDOTIR_WITHDRAW_KEY')},
                json={
                    'walletid': wallet_id,
                    'amount': self.amount * 10,
                    'name': self.bank_account.user.get_full_name(),
                    'iban': self.bank_account.iban,
                    'uid': self.pk,
                }
            )
            if second_resp.json()['success']:
                self.provider_request_status = FiatWithdrawRequest.SENT
                self.save()
            else:
                logger.error(
                    'Bank transfer registration failed'
                )
                return

    def update_provider_request_status(self):
        resp = requests.get(
            self.BASE_URL + '/api/v2/cashouts/%s' % self.pk,
            headers={'Authorization': '%s' % secret('PAYDOTIR_WITHDRAW_KEY')},
        )
        resp_json = resp.json()
        if resp_json['success']:
            if resp_json['data']['id'] == 4:
                self.provider_request_status = DONE
                self.status = DONE
            if resp_json['data']['id'] == (5 or 3):
                self.provider_request_status = CANCELED
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

            if self.status != PENDING:
                self.lock.release()

        self.alert_withdraw_verify_status(old)

    def __str__(self):
        return '%s %s' % (self.bank_account, self.amount)

    class Meta:
        verbose_name = 'درخواست برداشت'
        verbose_name_plural = 'درخواست‌های برداشت'
