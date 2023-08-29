from collections import namedtuple
from decimal import Decimal

from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models import CheckConstraint, Q

from accounts.models import Account
from ledger.utils.fields import get_amount_field

DEFAULT_MAKER_FEE = 0
# DEFAULT_TAKER_FEE = 0
DEFAULT_TAKER_FEE = Decimal('0.002')


class PairSymbol(models.Model):
    IdName = namedtuple("PairSymbol", "id name tick_size")

    name = models.CharField(max_length=32, blank=True, unique=True)
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT, related_name='pair')
    base_asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT, related_name='trading_pair')

    taker_fee = models.DecimalField(max_digits=9, decimal_places=8, default=DEFAULT_TAKER_FEE)
    maker_fee = models.DecimalField(max_digits=9, decimal_places=8, default=DEFAULT_MAKER_FEE)

    tick_size = models.PositiveSmallIntegerField(default=2, validators=[MaxValueValidator(8)])
    step_size = models.PositiveSmallIntegerField(default=4, validators=[MaxValueValidator(8)])
    min_trade_quantity = get_amount_field(default=Decimal('0.0001'))
    max_trade_quantity = get_amount_field(default=Decimal('10000'))

    enable = models.BooleanField(default=False)
    strategy_enable = models.BooleanField(default=False)

    last_trade_time = models.DateTimeField(null=True, blank=True)
    last_trade_price = get_amount_field(null=True)

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
        constraints = [
            CheckConstraint(check=Q(min_trade_quantity__gte=0, max_trade_quantity__gte=0,), name='check_market_pairsymbol_amounts', ),
        ]

    def get_fee_rate(self, account: Account, is_maker: bool) -> Decimal:
        if account.is_system():
            return Decimal(0)

        if account.get_voucher_wallet():
            return Decimal(0)
        else:
            return self.maker_fee if is_maker else self.taker_fee
