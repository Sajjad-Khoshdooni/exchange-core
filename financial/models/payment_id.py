from decimal import Decimal

from django.conf import settings
from django.db import models
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from decouple import config

from accounts.models import Account
from accounts.models import Notification
from accounts.utils import email
from ledger.models import Trx, Asset
from ledger.utils.fields import DONE
from ledger.utils.fields import get_group_id_field, get_status_field
from ledger.utils.precision import humanize_number, get_presentation_amount
from ledger.utils.wallet_pipeline import WalletPipeline


class PaymentIdRequest(models.Model):
    IN_PROGRESS, WAITING_FOR_MERCHANT_VERIFY, FAILED, SUCCESSFUL = \
        'IN_PROGRESS', ' WAITING_FOR_MERCHANT_VERIFY', 'FAILED', 'SUCCESSFUL'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    gateway = models.ForeignKey('financial.Gateway', on_delete=models.PROTECT)
    bank_account = models.ForeignKey('financial.BankAccount', on_delete=models.PROTECT)

    amount = models.PositiveIntegerField()
    bank = models.CharField(max_length=16)
    bank_reference_number = models.IntegerField()
    destination_account_identifier = models.CharField(max_length=100)  # todo check max length
    external_reference_number = models.IntegerField()
    payment_id = models.IntegerField(unique=True)
    raw_bank_timestamp = models.DateTimeField()
    status = models.CharField(
        max_length=30,
        choices=[
            (IN_PROGRESS, IN_PROGRESS), (WAITING_FOR_MERCHANT_VERIFY, WAITING_FOR_MERCHANT_VERIFY),
            (FAILED, FAILED), (SUCCESSFUL, SUCCESSFUL)
        ],
        default=IN_PROGRESS
    )

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
                    'brand': settings.BRAND,
                    'panel_url': settings.PANEL_URL,
                    'logo_elastic_url': config('LOGO_ELASTIC_URL'),
                }
            )
