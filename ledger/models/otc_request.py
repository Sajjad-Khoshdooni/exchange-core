from django.db import models

from account.models import Account
from ledger.models import Asset, Order
from ledger.utils.fields import get_amount_field
from ledger.utils.random import secure_uuid4


class OTCRequest(models.Model):
    EXPIRE_TIME = 5

    created = models.DateTimeField(auto_now_add=True)
    token = models.UUIDField(default=secure_uuid4, db_index=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE)

    coin = models.ForeignKey(to=Asset, on_delete=models.CASCADE)
    side = models.CharField(max_length=8, choices=Order.ORDER_CHOICES)
    price = get_amount_field()

    def __str__(self):
        return '%s - %s' % (self.coin, self.side)