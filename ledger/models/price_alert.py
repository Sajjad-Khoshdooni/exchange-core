from django.db import models

from accounts.models import User
from ledger.models import Asset


class PriceTracking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'asset'], name='price_tracking_idx')
        ]
        unique_together = [('user', 'asset')]
