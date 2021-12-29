from django.db import models
from uuid import uuid4
from ledger.utils.constants import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES


class Trx(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)

    group_id = models.UUIDField(default=uuid4, db_index=True)
