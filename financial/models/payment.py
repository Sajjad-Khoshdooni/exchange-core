from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Account
from ledger.models import Trx, Asset
from ledger.utils.fields import get_group_id_field, get_status_field

from accounts.models import Notification
from accounts.utils import email
from ledger.utils.precision import humanize_number, get_presentation_amount


class PaymentRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    gateway = models.ForeignKey('financial.Gateway', on_delete=models.PROTECT)
    bank_card = models.ForeignKey('financial.BankCard', on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()

    authority = models.CharField(max_length=64, blank=True, db_index=True)

    @property
    def rial_amount(self):
        return 10 * self.amount

    def get_gateway(self):
        return self.gateway.get_concrete_gateway()

    class Meta:
        unique_together = [('authority', 'gateway')]


class Payment(models.Model):

    SUCCESS_URL = 'https://raastin.com/checkout/success'
    FAIL_URL = 'https://raastin.com/checkout/fail'

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
        title = 'واریز وجه با موفقیت انجام شد'
        payment_amont = humanize_number(get_presentation_amount(Decimal(self.payment_request.amount)))
        description = 'مبلغ {} با موفقیت به حساب شما واریز شد'.format(payment_amont)

        Notification.send(
            recipient=user,
            title=title,
            message=description,
            level=Notification.SUCCESS
        )
        email.send_email_by_template(
            recipient=user.email,
            template=email.SCOPE_PAYMENT,
            context={'payment_amount': payment_amont}
        )

    def accept(self):
        asset = Asset.get(Asset.IRT)
        user = self.payment_request.bank_card.user
        account = user.account

        Trx.transaction(
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
