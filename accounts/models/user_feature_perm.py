from django.db import models


class UserFeaturePerm(models.Model):
    FEATURES = PAY_ID, = 'pay_id',

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    feature = models.CharField(max_length=16, choices=[(f, f) for f in FEATURES])

    class Meta:
        unique_together = ('user', 'feature')
