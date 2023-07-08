from django.core.validators import validate_integer
from django.db import models

from financial.models import Payment
from financial.validators import iban_validator
from ledger.utils.fields import get_status_field, DONE, PENDING
from ledger.utils.wallet_pipeline import WalletPipeline


class PaymentId(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    gateway = models.ForeignKey('financial.Gateway', on_delete=models.PROTECT)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    pay_id = models.CharField(max_length=32, validators=[validate_integer])
    verified = models.BooleanField(default=False)

    destination = models.ForeignKey('financial.GeneralBankAccount', on_delete=models.PROTECT)

    def __str__(self):
        return self.pay_id

    class Meta:
        unique_together = [('user', 'gateway'), ('pay_id', 'gateway')]


class PaymentIdRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    payment_id = models.ForeignKey(PaymentId, on_delete=models.PROTECT)
    status = get_status_field()

    amount = models.PositiveIntegerField()
    fee = models.PositiveIntegerField()

    bank_ref = models.CharField(max_length=64, blank=True)
    external_ref = models.CharField(max_length=64, blank=True, unique=True)

    source_iban = models.CharField(
        max_length=26,
        validators=[iban_validator],
        verbose_name='شبا',
    )

    deposit_time = models.DateTimeField()

    payment = models.OneToOneField('financial.Payment', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return '%s ref=%s' % (self.amount, self.bank_ref)

    def accept(self):
        if not self.payment_id:
            return

        with WalletPipeline() as pipeline:
            req = PaymentIdRequest.objects.select_for_update().get(id=self.id)

            if req.payment or req.status != PENDING:
                return

            req.payment = Payment.objects.create(
                status=DONE,
                ref_id=req.bank_ref,
            )
            req.payment.accept(pipeline)

            req.status = DONE
            req.save(update_fields=['status', 'payment'])
