from django.db import models

from accounts.models import User
from ledger.models import Asset
from ledger.utils.fields import get_amount_field


class AlertTrigger(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    coin = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='symbol')
    price = get_amount_field()
    cycle = models.PositiveIntegerField()
    is_triggered = models.BooleanField()

    class Meta:
        unique_together = ('coin', 'cycle')
        indexes = [
            models.Index(fields=['coin', 'cycle', 'is_triggered'], name='alert_trigger_idx')
        ]


class AssetAlert(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('user', 'asset')]
