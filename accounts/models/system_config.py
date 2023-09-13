from django.db import models

from ledger.utils.fields import get_amount_field

from decimal import Decimal


class SystemConfig(models.Model):
    active = models.BooleanField()
    is_consultation_available = models.BooleanField(default=False)

    ipg_withdraw_fee_min = models.SmallIntegerField(default=1000)
    ipg_withdraw_fee_max = models.SmallIntegerField(default=5000)
    ipg_withdraw_fee_percent = get_amount_field(default=Decimal('0.05'))

    @classmethod
    def get_system_config(cls) -> 'SystemConfig':
        return SystemConfig.objects.filter(
            active=True
        ).first() or SystemConfig()
