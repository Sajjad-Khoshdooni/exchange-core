import math

from django.db import models

from ledger.consts import BEP20_SYMBOL_TO_SMART_CONTRACT
from ledger.utils.fields import COMMISSION_MAX_DIGITS, get_amount_field


class NetworkAsset(models.Model):
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)

    withdraw_fee = get_amount_field(max_digits=COMMISSION_MAX_DIGITS)
    withdraw_min = get_amount_field(max_digits=COMMISSION_MAX_DIGITS)
    withdraw_max = get_amount_field()
    withdraw_precision = models.PositiveSmallIntegerField()

    binance_withdraw_enable = models.BooleanField(default=True)

    def can_deposit(self):
        if not self.network.can_deposit:
            return False
        elif self.network.symbol == 'TRX':
            return self.asset.symbol in ('TRX', 'USDT')
        elif self.network.symbol == 'BSC':
            return self.asset.symbol in BEP20_SYMBOL_TO_SMART_CONTRACT
        else:
            return False

    def __str__(self):
        return '%s - %s' % (self.network, self.asset)

    class Meta:
        unique_together = ('asset', 'network')
