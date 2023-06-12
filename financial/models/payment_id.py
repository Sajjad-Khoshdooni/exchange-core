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

    bank_ref = models.CharField(max_length=64, blank=True)
    external_ref = models.CharField(max_length=64, blank=True, unique=True)

    source_iban = models.CharField(
        max_length=26,
        validators=[iban_validator],
        verbose_name='شبا',
        unique=True
    )

    def accept(self):
        with WalletPipeline() as pipeline:
            req = PaymentIdRequest.objects.select_for_update().get(id=self.id)

            if req is not PENDING:
                return

            payment = Payment.objects.create(
                payment_id_request=req,
                status=Payment.SUCCESS,
                ref_id=req.bank_ref,
            )
            payment.accept(pipeline)

            req.status = DONE
            req.save(update_fields=['status'])
