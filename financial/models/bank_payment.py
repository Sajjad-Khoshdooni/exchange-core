from django.core.exceptions import ValidationError
from django.db import models

from financial.models import Payment
from ledger.utils.fields import get_group_id_field

DESTINATION_TYPES = JIBIMO, = 'jibimo',


class BankPayment(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    payment_created = models.DateTimeField()
    destination_type = models.CharField(max_length=16, default=JIBIMO, choices=[(d, d) for d in DESTINATION_TYPES])
    destination_id = models.PositiveIntegerField()

    amount = models.PositiveIntegerField()
    fee = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    def __str__(self):
        return '%s IRT (%s %s)' % (self.amount, self.destination_type, self.destination_id)

    class Meta:
        unique_together = ('destination_id', 'destination_type')


class BankPaymentRequest(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    group_id = get_group_id_field()

    destination_type = models.CharField(max_length=16, default=JIBIMO, choices=[(d, d) for d in DESTINATION_TYPES])
    amount = models.PositiveIntegerField()
    ref_id = models.CharField(blank=True, max_length=256)
    receipt = models.FileField()

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True)
    bank_payment = models.OneToOneField(BankPayment, on_delete=models.SET_NULL, null=True, blank=True)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return '%s %s' % (self.user, self.bank_payment)

    def clean(self):
        if self.bank_payment and self.amount != self.bank_payment.amount:
            raise ValidationError('amount mismatch with bank_payment')

    def create_payment(self):
        if self.payment:
            return self.payment
