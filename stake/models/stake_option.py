from django.db import models

from ledger.models import Asset


class StakeOption(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    apr = models.DecimalField(max_digits=6, decimal_places=3, blank=True)

    enable = models.BooleanField(default=False)

    def __str__(self):
        return self.asset.symbol

