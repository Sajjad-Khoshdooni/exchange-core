from django.db import models

from ledger.utils.fields import get_amount_field


class UserFeaturePerm(models.Model):
    FEATURES = PAY_ID, FIAT_DEPOSIT_LIMIT = 'pay_id', 'fiat_deposit_limit'

    DEFAULT_LIMITS = {
        FIAT_DEPOSIT_LIMIT: 200_000_000
    }

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    feature = models.CharField(max_length=32, choices=[(f, f) for f in FEATURES])
    limit = get_amount_field(null=True)

    class Meta:
        unique_together = ('user', 'feature')
