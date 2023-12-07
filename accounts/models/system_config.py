from django.db import models

from ledger.utils.fields import get_amount_field

from decimal import Decimal


class SystemConfig(models.Model):
    active = models.BooleanField()
    is_consultation_available = models.BooleanField(default=False)

    withdraw_fee_min = models.SmallIntegerField(default=1000)
    withdraw_fee_max = models.SmallIntegerField(default=5000)
    withdraw_fee_percent = get_amount_field(default=Decimal('5'))

    hedge_irt_by_internal_market = models.BooleanField(default=False)

    @classmethod
    def get_system_config(cls) -> 'SystemConfig':
        return SystemConfig.objects.filter(
            active=True
        ).first() or SystemConfig()
