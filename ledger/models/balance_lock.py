from django.db import models

from ledger.utils import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES


class BalanceLock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    release_date = models.DateTimeField()

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=AMOUNT_MAX_DIGITS, decimal_places=AMOUNT_DECIMAL_PLACES)
    freed = models.BooleanField(default=False, db_index=True)

