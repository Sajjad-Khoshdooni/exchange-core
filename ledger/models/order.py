from uuid import uuid4

from django.db import models

from ledger.utils.fields import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES, get_amount_field


class Order(models.Model):
    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    PENDING, CANCELLED, DONE = 'pend', 'cancel', 'done'

    created = models.DateTimeField(auto_now_add=True)

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)
    amount = get_amount_field()
    group_id = models.UUIDField(default=uuid4, db_index=True)
    type = models.CharField(max_length=8, choices=ORDER_CHOICES)
    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELLED, CANCELLED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE)
