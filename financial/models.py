from uuid import uuid4

from django.db import models

from accounts.models import Account


class FiatTransferRequest(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done',

    created = models.DateTimeField(auto_now_add=True)
    group_id = models.UUIDField(default=uuid4, db_index=True)

    account = models.ForeignKey(to=Account, on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()

    deposit = models.BooleanField(default=False)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        db_index=True
    )

    transaction = models.OneToOneField('ledger.Trx', on_delete=models.PROTECT)
