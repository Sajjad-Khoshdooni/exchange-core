from django.db import models

from ledger.models import Asset


class StakeOption(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    _yield = models.DecimalField(max_digits=12, decimal_places=6, blank=True)

    enable = models.BooleanField(default=False)



