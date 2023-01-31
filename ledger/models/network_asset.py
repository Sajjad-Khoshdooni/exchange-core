import math
from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q

from ledger.utils.fields import get_amount_field
from ledger.utils.price import get_trading_price_usdt, BUY


class NetworkAsset(models.Model):
    asset = models.ForeignKey('ledger.Asset', on_delete=models.PROTECT)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)

    withdraw_fee = get_amount_field()
    withdraw_min = get_amount_field()
    withdraw_max = get_amount_field()
    withdraw_precision = models.PositiveSmallIntegerField()

    hedger_withdraw_enable = models.BooleanField(default=True)
    hedger_deposit_enable = models.BooleanField(default=True)

    can_deposit = models.BooleanField(default=False)
    can_withdraw = models.BooleanField(default=True)

    allow_provider_withdraw = models.BooleanField(default=True)

    def can_deposit_enabled(self) -> bool:
        return self.network.can_deposit and self.can_deposit and self.hedger_deposit_enable

    def can_withdraw_enabled(self) -> bool:
        return self.network.can_withdraw and self.can_withdraw and self.hedger_withdraw_enable

    def __str__(self):
        return '%s - %s' % (self.network, self.asset)

    class Meta:
        unique_together = ('asset', 'network')
        constraints = [
            CheckConstraint(check=Q(withdraw_fee__gte=0, withdraw_min__gte=0, withdraw_max__gte=0), name='check_ledger_network_amounts', ),
        ]

    def update_with_provider(self, info):
        symbol_pair = (self.network.symbol, self.asset.symbol)
        withdraw_fee = info.withdraw_fee
        withdraw_min = info.withdraw_min

        if symbol_pair in [('TRX', 'USDT'), ('BSC', 'USDT'), ('BNB', 'USDT'), ('SOL', 'USDT')]:
            withdraw_fee = Decimal('0.8')
            withdraw_min = Decimal(10)
        elif symbol_pair not in [('TRX', 'USDT'), ('TRX', 'TRX'), ('BSC', 'USDT'), ('BNB', 'USDT'), ('SOL', 'USDT')]:
            withdraw_fee *= 2
            withdraw_min = max(withdraw_min, 2 * withdraw_fee)

        price = get_trading_price_usdt(self.asset.symbol, BUY, raw_price=True)

        if price and withdraw_min:
            multiplier = max(math.ceil(5 / (price * withdraw_min)), 1)  # withdraw_min >= 5$
            withdraw_min *= multiplier

        if price and withdraw_fee:
            multiplier = max(math.ceil(Decimal('0.2') / (price * withdraw_fee)), 1)  # withdraw_fee >= 0.2$
            withdraw_fee *= multiplier

        withdraw_min = max(
            withdraw_min,
            info.withdraw_min + withdraw_fee - info.withdraw_fee
        )

        self.withdraw_fee = withdraw_fee
        self.withdraw_min = withdraw_min
        self.withdraw_max = info.withdraw_max
        self.hedger_withdraw_enable = info.withdraw_enable
        self.hedger_deposit_enable = info.deposit_enable
        self.save(update_fields=[
            'withdraw_fee', 'withdraw_min', 'withdraw_max', 'hedger_withdraw_enable', 'hedger_deposit_enable'
        ])
