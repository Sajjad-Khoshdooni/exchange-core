from django.db import models

from ledger.utils import COMMISSION_MAX_DIGITS, AMOUNT_DECIMAL_PLACES


class NetworkAsset(models.Model):
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    commission = models.DecimalField(max_digits=COMMISSION_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    min_transfer = models.DecimalField(max_digits=COMMISSION_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)

    class Meta:
        unique_together = ('asset', 'network')
