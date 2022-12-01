from django.db import models
from django.db.models import Case, When, Sum, F, IntegerField

from financial.validators import iban_validator


class Account(models.Model):
    name = models.CharField(max_length=64, verbose_name='نام')
    iban = models.CharField(max_length=26, verbose_name='شماره شبا', validators=[iban_validator],)
    description = models.TextField(verbose_name='توضیحات', blank=True)

    def __str__(self):
        return self.name

    def get_balance(self) -> int:
        return self.accounttransaction_set.annotate(
            real=Case(
                When(type='w', then=-F('amount')),
                default=F('amount'),
                output_field=IntegerField()
            )
        ).aggregate(s=Sum('real'))['s'] or 0

    class Meta:
        verbose_name = 'حساب'
        verbose_name_plural = 'حساب‌ها'
