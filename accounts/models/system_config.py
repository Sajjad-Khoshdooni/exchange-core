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
    hedge_coin_otc_from_internal_market = models.BooleanField(default=True)

    max_margin_leverage = models.SmallIntegerField(default=5)
    default_margin_leverage = models.SmallIntegerField(default=3)

    total_margin_usdt_base = get_amount_field(default=Decimal('10_000'))
    total_margin_irt_base = get_amount_field(default=Decimal('500_000_000'))
    total_user_margin_usdt_base = get_amount_field(default=Decimal('10_000'))
    total_user_margin_irt_base = get_amount_field(default=Decimal('500_000_000'))
    liquidation_level = get_amount_field(default=Decimal('1.1'))
    insurance_fee = get_amount_field(default=Decimal('0.02'))

    open_pay_id_to_all = models.BooleanField(default=False)

    @classmethod
    def get_system_config(cls) -> 'SystemConfig':
        return SystemConfig.objects.filter(
            active=True
        ).first() or SystemConfig()
