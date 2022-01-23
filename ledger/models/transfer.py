from uuid import uuid4

from django.db import models

from ledger.utils.fields import get_amount_field


class Transfer(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

    created = models.DateTimeField(auto_now_add=True)
    group_id = models.UUIDField(default=uuid4, db_index=True)
    network_wallet = models.ForeignKey('ledger.NetworkAddress', on_delete=models.CASCADE)

    amount = get_amount_field()
    deposit = models.BooleanField()

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    lock = models.OneToOneField('ledger.BalanceLock', on_delete=models.CASCADE)

    trx_hash = models.CharField(max_length=128, db_index=True, unique=True)
    block_hash = models.CharField(max_length=128, db_index=True, unique=True, blank=True)
    block_number = models.PositiveIntegerField(null=True, blank=True)

    out_address = models.CharField(max_length=256)
