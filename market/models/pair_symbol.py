from collections import namedtuple
from decimal import Decimal

from django.db import models

from ledger.models import Asset
from ledger.utils.fields import get_amount_field

DEFAULT_MAKER_FEE = 0
DEFAULT_TAKER_FEE = Decimal('0.002')


class PairSymbol(models.Model):
    IdName = namedtuple("PairSymbol", "id name")

    name = models.CharField(max_length=32, blank=True, unique=True)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='pair')
    base_asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='trading_pair')

    taker_fee = models.DecimalField(max_digits=9, decimal_places=8, default=DEFAULT_TAKER_FEE)
    maker_fee = models.DecimalField(max_digits=9, decimal_places=8, default=DEFAULT_MAKER_FEE)

    tick_size = models.SmallIntegerField(default=2)
    step_size = models.SmallIntegerField(default=4)
    min_trade_quantity = get_amount_field(default=Decimal('0.0001'))
    max_trade_quantity = get_amount_field(default=Decimal('10000'))

    market_maker_enabled = models.BooleanField(default=True)
    maker_amount = get_amount_field(default=Decimal('1'))

    enable = models.BooleanField(default=False)

    @classmethod
    def get_by(cls, name):
        return cls.objects.get(name=name)

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        self.name = f'{self.asset}{self.base_asset}'
        if not self.name:
            raise Exception('Could not set name for pair symbol!')
        return super(PairSymbol, self).save(**kwargs)

    class Meta:
        unique_together = ('asset', 'base_asset')
