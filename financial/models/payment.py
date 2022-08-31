from decimal import Decimal

from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from yekta_config.config import config
from accounts.models import Account
from ledger.models import Trx, Asset
from ledger.utils.fields import get_group_id_field, get_status_field
from accounts.models import Notification
from accounts.utils import email
from ledger.utils.precision import humanize_number, get_presentation_amount
from ledger.utils.wallet_pipeline import WalletPipeline
from ledger.utils.fields import DONE, CANCELED


class PaymentRequest(models.Model):

    APP, DESKTOP = 'app', 'desktop'
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    gateway = models.ForeignKey('financial.Gateway', on_delete=models.PROTECT)
    bank_card = models.ForeignKey('financial.BankCard', on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()

    source = models.CharField(max_length=16, choices=((APP, APP), (DESKTOP, DESKTOP)), default=DESKTOP)

    authority = models.CharField(max_length=64, blank=True, db_index=True)

    @property
    def rial_amount(self):
        return 10 * self.amount

    def get_gateway(self):
        return self.gateway.get_concrete_gateway()

    class Meta:
        unique_together = [('authority', 'gateway')]

    def __str__(self):
        return '%s %s' % (self.gateway, self.bank_card)


class Payment(models.Model):
    APP_DEEP_LINK = config('APP_DEEP_LINK')
    PANEL_URL = config('PANEL_URL')
    SUCCESS_URL = '/checkout/success'
    FAIL_URL = '/checkout/fail'
    APP_SUCCESS_URL = '/Checkout/success'
    APP_FAIL_URL = '/Checkout/fail'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    PENDING, SUCCESS, FAIL = 'pending', 'success', 'fail'

    group_id = get_group_id_field()

    payment_request = models.OneToOneField(PaymentRequest, on_delete=models.PROTECT)

    status = get_status_field()

    ref_id = models.PositiveBigIntegerField(null=True, blank=True)
    ref_status = models.SmallIntegerField(null=True, blank=True)

    def alert_payment(self):
        user = self.payment_request.bank_card.user
        user_email = user.email
        title = 'واریز وجه با موفقیت انجام شد'
        payment_amont = humanize_number(get_presentation_amount(Decimal(self.payment_request.amount)))
        description = 'مبلغ {} تومان به حساب شما واریز شد'.format(payment_amont)

        Notification.send(
            recipient=user,
            title=title,
            message=description,
            level=Notification.SUCCESS
        )

        if user_email:
            email.send_email_by_template(
                recipient=user_email,
                template=email.SCOPE_PAYMENT,
                context={
                    'payment_amount': payment_amont,
                    'brand': config('BRAND'),
                    'panel_url': config('PANEL_URL'),
                    'logo_elastic_url': config('LOGO_ELASTIC_URL'),
                         }
            )

    def accept(self, pipeline: WalletPipeline):
        asset = Asset.get(Asset.IRT)
        user = self.payment_request.bank_card.user
        account = user.account

        pipeline.new_trx(
            sender=asset.get_wallet(Account.out()),
            receiver=asset.get_wallet(account),
            amount=self.payment_request.amount,
            scope=Trx.TRANSFER,
            group_id=self.group_id,
        )

        if not user.first_fiat_deposit_date:
            user.first_fiat_deposit_date = timezone.now()
            user.save()

        self.alert_payment()

    def get_redirect_url(self) -> str:
        source = self.payment_request.source
        desktop = PaymentRequest.DESKTOP

        if source == desktop:
            if self.status == DONE:
                return self.PANEL_URL + self.SUCCESS_URL
            else:
                return self.PANEL_URL + self.FAIL_URL
        else:
            if self.status == DONE:
                return self.APP_DEEP_LINK + self.APP_SUCCESS_URL
            else:
                return self.APP_DEEP_LINK + self.APP_FAIL_URL

    def redirect_to_app(self):
        url = self.get_redirect_url()

        if url.startswith('http'):
            return redirect(url)
        else:
            return 'intent://Checkout/fail/#Intent;scheme=raastin;package=com.raastinappts;end'
            response = HttpResponse("", status=302)
            response['Location'] = url
            return response
