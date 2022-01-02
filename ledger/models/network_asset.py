from django.db import models

from ledger.utils.fields import COMMISSION_MAX_DIGITS, AMOUNT_DECIMAL_PLACES, get_amount_field


class NetworkAsset(models.Model):
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    commission = get_amount_field(max_digits=COMMISSION_MAX_DIGITS)
    min_transfer = get_amount_field(max_digits=COMMISSION_MAX_DIGITS)

    def __str__(self):
        return '%s - %s' % (self.network, self.asset)

    class Meta:
        unique_together = ('asset', 'network')
