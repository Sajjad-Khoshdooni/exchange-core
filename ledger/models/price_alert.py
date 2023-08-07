from django.db import models

from accounts.models import User
from ledger.models import Asset


class PriceTracking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    assets = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('user', 'asset')]
