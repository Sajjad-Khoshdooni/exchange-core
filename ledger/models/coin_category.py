from django.db import models

from ledger.models import Asset


class CoinCategory(models.Model):
    name = models.CharField(max_length=30)
    coin = models.ManyToManyField(Asset, null=True, blank=True)
