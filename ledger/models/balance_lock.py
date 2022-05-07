from django.db import models
from django.db.models import CheckConstraint, Q
from django.utils import timezone

from ledger.utils.fields import get_amount_field


class BalanceLock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    release_date = models.DateTimeField(null=True, blank=True)

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)
    amount = get_amount_field()
    freed = models.BooleanField(default=False, db_index=True)

    def release(self):
        if not self.freed:
            self.freed = True
            self.release_date = timezone.now()
            self.save()

    def __str__(self):
        return '%s %s %s' % (self.wallet, self.wallet.asset.get_presentation_amount(self.amount), self.freed)

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_amount', ), ]
