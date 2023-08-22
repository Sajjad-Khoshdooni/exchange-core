from django.db import models

from accounts.models import User
from ledger.models import Asset
from ledger.utils.fields import get_amount_field

MINUTES = 'پنج‌ دقیقه'
HOUR = '‌یک‌ ساعت'


class AlertTrigger(models.Model):
    INTERVAL_CHOICES = [
        ('5m', MINUTES),
        ('1h', HOUR)
    ]
    created = models.DateTimeField(auto_now_add=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    price = get_amount_field()
    change_percent = models.IntegerField(default=0)
    cycle = models.PositiveIntegerField()
    interval = models.CharField(choices=INTERVAL_CHOICES, max_length=15)
    is_triggered = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['is_triggered', 'asset', 'created'], name='alert_trigger_idx')
        ]


class AssetAlert(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)

    class Meta:
        unique_together = [('user', 'asset')]
