from uuid import uuid4

from django.db import models

from ledger.utils.fields import get_amount_field


class Transfer(models.Model):
    PENDING, CANCELLED, DONE = 'pend', 'cancel', 'done'

    created = models.DateTimeField(auto_now_add=True)

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)

    amount = get_amount_field()
    group_id = models.UUIDField(default=uuid4, db_index=True)
    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELLED, CANCELLED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE)

    out_address = models.CharField(max_length=256)
