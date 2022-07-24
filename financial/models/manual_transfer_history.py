from decimal import Decimal

from django.db import models

from ledger.utils.fields import get_amount_field


class ManualTransferHistory(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    asset = models.ForeignKey(to='ledger.Asset', on_delete=models.PROTECT)
    amount = get_amount_field()
    full_fill_amount = get_amount_field(default=Decimal(0))
    reason = models.TextField()
    deposit = models.BooleanField()
