from django.db import models

from ledger.models import Asset
from ledger.utils.fields import get_amount_field


class StakeOption(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    apr = models.DecimalField(max_digits=6, decimal_places=3, blank=True)
    enable = models.BooleanField(default=False)
    max_amount = get_amount_field()
    min_amont = get_amount_field()

    def __str__(self):
        return self.asset.symbol + ' ' + str(self.apr)

