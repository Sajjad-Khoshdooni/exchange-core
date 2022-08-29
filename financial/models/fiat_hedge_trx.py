from django.db import models

from ledger.utils.fields import get_amount_field


class FiatHedgeTrx(models.Model):
    TRADE, MANUAL = 't', 'm'

    created = models.DateTimeField(auto_now_add=True)
    base_amount = get_amount_field(validators=())
    target_amount = get_amount_field(validators=())
    price = get_amount_field(validators=())

    source = models.CharField(max_length=1, choices=((TRADE, 'trade'), (MANUAL, 'manual')))
    reason = models.CharField(max_length=64, blank=True)

