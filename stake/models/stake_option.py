from django.db import models
from django.db.models import Sum

from ledger.models import Asset
from ledger.utils.fields import get_amount_field
from accounts.models import User


class StakeOption(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    apr = models.DecimalField(max_digits=6, decimal_places=3, blank=True)

    user_max_amount = get_amount_field()
    user_min_amount = get_amount_field()

    total_cap = get_amount_field()

    enable = models.BooleanField(default=False)

    def __str__(self):
        return self.asset.symbol + ' ' + str(self.apr)

    def get_free_cap_amount(self):
        from stake.models import StakeRequest
        cap = self.total_cap
        filled_cap = StakeRequest.objects.filter(
            stake_option=self,
            status__in=(StakeRequest.PROCESS, StakeRequest.PENDING, StakeRequest.DONE),
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        return cap - filled_cap

    def get_filled_cap_percent(self):

        return (1 - self.get_free_cap_amount() / self.total_cap) * 100

    def get_free_amount_per_user(self, user: User):
        from stake.models import StakeRequest

        total_stake_amount = StakeRequest.objects.filter(
            stake_option=self,
            account__user=user
        ).exclude(status=StakeRequest.CANCEL_COMPLETE).aggregate(Sum('amount'))['amount__sum'] or 0

        return self.user_max_amount - total_stake_amount
