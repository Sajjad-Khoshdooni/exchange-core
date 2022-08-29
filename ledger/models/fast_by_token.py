from django.db import models

from financial.models import PaymentRequest
from ledger.models import Asset
from ledger.utils.fields import get_amount_field


class FastBuyToken(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    price = get_amount_field(null=True)
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE())

