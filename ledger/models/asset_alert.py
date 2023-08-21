from django.db import models

from accounts.models import User
from ledger.models import Asset
from ledger.utils.fields import get_amount_field


class AlertTrigger(models.Model):
    created = models.DateTimeField(auto_created=True)
    coin = models.CharField()
    price = get_amount_field()
    cycle = models.PositiveIntegerField()
    is_triggered = models.BooleanField()

    class Meta:
        indexes = [
            models.Index(['asset', 'cycle', 'is_triggered'])
        ]


class AssetAlert(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('user', 'asset')]
