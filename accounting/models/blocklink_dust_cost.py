from django.db import models
from simple_history.models import HistoricalRecords


class BlocklinkDustCost(models.Model):
    history = HistoricalRecords()

    updated = models.DateTimeField(auto_now=True)
    amount = models.PositiveIntegerField()
    usdt_value = models.PositiveIntegerField()
    network = models.CharField(max_length=16)
    coin = models.CharField(max_length=16)
