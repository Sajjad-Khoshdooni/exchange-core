from django.core.validators import validate_integer
from django.db import models

from financial.models import Payment
from financial.validators import iban_validator
from ledger.utils.fields import get_status_field, DONE, PENDING, get_group_id_field
from ledger.utils.wallet_pipeline import WalletPipeline


class PaymentId(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    gateway = models.ForeignKey('financial.Gateway', on_delete=models.PROTECT)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    pay_id = models.CharField(max_length=32, validators=[validate_integer])
    verified = models.BooleanField(default=False)

    destination = models.ForeignKey('financial.GeneralBankAccount', on_delete=models.PROTECT)

    group_id = get_group_id_field()

    provider_status = models.CharField(max_length=256, blank=True)
    provider_reason = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return self.pay_id

    class Meta:
        unique_together = [('user', 'gateway'), ('pay_id', 'gateway')]


class PaymentIdRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    owner = models.ForeignKey(PaymentId, on_delete=models.PROTECT)
    status = get_status_field()

    amount = models.PositiveBigIntegerField()
    fee = models.PositiveBigIntegerField()

    bank_ref = models.CharField(max_length=64, blank=True)
    external_ref = models.CharField(max_length=64, blank=True, unique=True)

    source_iban = models.CharField(
        max_length=26,
        validators=[iban_validator],
        verbose_name='شبا',
    )

    deposit_time = models.DateTimeField()

    group_id = get_group_id_field()
    payment = models.OneToOneField('financial.Payment', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return '%s ref=%s' % (self.amount, self.bank_ref)

    def accept(self):
        with WalletPipeline() as pipeline:
            req = PaymentIdRequest.objects.select_for_update().get(id=self.id)

            if req.payment or req.status != PENDING:
                return

            req.payment = Payment.objects.create(
                group_id=req.group_id,
                user=req.owner.user,
                amount=req.amount,
                fee=req.fee,
            )
            req.payment.accept(pipeline, req.bank_ref)

            req.status = DONE
            req.save(update_fields=['status', 'payment'])
