from django.db import models

from accounts.models import User
from ledger.models import Asset
from ledger.utils.fields import get_amount_field

MINUTES = 'پنج‌ دقیقه'
HOUR = '‌یک‌ ساعت'


class AlertTrigger(models.Model):
    INTERVAL_CHOICES = [
        (MINUTES, MINUTES),
        (HOUR, HOUR)
    ]
    created = models.DateTimeField(auto_now_add=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, to_field='symbol')
    price = get_amount_field()
    cycle = models.PositiveIntegerField()
    interval = models.CharField(choices=INTERVAL_CHOICES, max_length=15)
    is_triggered = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['asset', 'created', 'is_triggered'], name='alert_trigger_idx')
        ]


class AssetAlert(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('user', 'asset')]
