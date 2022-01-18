from django.db import models
from django.utils import timezone

from ledger.utils.fields import AMOUNT_MAX_DIGITS, AMOUNT_DECIMAL_PLACES, get_amount_field


class BalanceLock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    release_date = models.DateTimeField()

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)
    amount = get_amount_field()
    freed = models.BooleanField(default=False, db_index=True)

    def release(self):
        if not self.freed:
            self.freed = True
            self.release_date = timezone.now()
            self.save()
