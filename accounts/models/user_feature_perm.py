from django.db import models

from ledger.utils.fields import get_amount_field


class UserFeaturePerm(models.Model):
    FEATURES = PAY_ID, FIAT_DEPOSIT_DAILY_LIMIT, BANK_PAYMENT, UI = 'pay_id', 'fiat_deposit_daily_limit', 'bank_payment', 'ui'

    DEFAULT_LIMITS = {
        FIAT_DEPOSIT_DAILY_LIMIT: 200_000_000
    }

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, verbose_name='کاربر')
    feature = models.CharField(max_length=32, choices=[(f, f) for f in FEATURES], verbose_name='ویژگی')
    limit = get_amount_field(null=True, verbose_name='محدودیت')
    custom = models.CharField(max_length=64, blank=True, verbose_name='پارامتر اختصاصی')

    class Meta:
        unique_together = ('user', 'feature', 'custom')
        verbose_name = 'دسترسی‌ کاربر'
        verbose_name_plural = 'دسترسی‌های کاربر'
