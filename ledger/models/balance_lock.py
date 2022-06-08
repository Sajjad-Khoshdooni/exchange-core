import logging
from decimal import Decimal

from django.db import models, transaction
from django.db.models import CheckConstraint, Q, F
from django.utils import timezone

from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


class BalanceLock(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    release_date = models.DateTimeField(null=True, blank=True)

    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.CASCADE)
    amount = get_amount_field()
    freed = models.BooleanField(default=False, db_index=True)

    def release(self):
        self.refresh_from_db()

        if self.freed:
            return

        from ledger.models import Wallet

        with transaction.atomic():
            self.freed = True
            self.release_date = timezone.now()
            self.save(update_fields=['freed', 'release_date'])

            Wallet.objects.filter(id=self.wallet_id).update(locked=F('locked') - self.amount)

    def decrease_lock(self, amount: Decimal):
        assert amount > 0

        from ledger.models import Wallet

        with transaction.atomic():
            BalanceLock.objects.filter(id=self.id).update(amount=F('amount') - amount)
            Wallet.objects.filter(id=self.wallet_id).update(locked=F('locked') - amount)

    @classmethod
    def new_lock(cls, wallet, amount: Decimal):
        assert amount > 0

        from ledger.models import Wallet

        with transaction.atomic():
            lock = BalanceLock.objects.create(
                wallet=wallet,
                amount=amount
            )

            Wallet.objects.filter(id=wallet.id).update(locked=F('locked') + amount)

            return lock

    def __str__(self):
        return '%s %s %s' % (self.wallet, self.wallet.asset.get_presentation_amount(self.amount), self.freed)

    class Meta:
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_amount', ), ]
