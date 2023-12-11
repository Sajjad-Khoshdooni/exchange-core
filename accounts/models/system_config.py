from django.db import models

from ledger.utils.fields import get_amount_field

from decimal import Decimal


class SystemConfig(models.Model):
    active = models.BooleanField()
    is_consultation_available = models.BooleanField(default=False)

    withdraw_fee_min = models.SmallIntegerField(default=1000)
    withdraw_fee_max = models.SmallIntegerField(default=5000)
    withdraw_fee_percent = get_amount_field(default=Decimal('5'))

    max_margin_leverage = get_amount_field(default=Decimal('5'))
    total_margin_usdt_base = get_amount_field(default=Decimal('10_000'))
    total_margin_irt_base = get_amount_field(default=Decimal('500_000_000'))
    total_user_margin_usdt_base = get_amount_field(default=Decimal('10_000'))
    total_user_margin_irt_base = get_amount_field(default=Decimal('500_000_000'))

    @classmethod
    def get_system_config(cls) -> 'SystemConfig':
        return SystemConfig.objects.filter(
            active=True
        ).first() or SystemConfig()
