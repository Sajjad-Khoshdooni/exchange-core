from django.db import models

from accounts.models import User
from ledger.models import Asset
from ledger.utils.fields import get_amount_field


class AlertTrigger(models.Model):
    FIVE_MIN = '5m'
    HOUR = '1h'

    INTERVAL_CHOICES = [
        (FIVE_MIN, 'پنج‌ دقیقه'),
        (HOUR, '‌یک‌ ساعت')
    ]

    INTERVAL_VERBOSE_MAP = dict(INTERVAL_CHOICES)

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
