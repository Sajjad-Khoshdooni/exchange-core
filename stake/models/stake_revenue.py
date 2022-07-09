from django.db import models

from ledger.utils.fields import get_group_id_field
from stake.models import StakeRequest


class StakeRevenue(models.Model):
    created = models.DateField(auto_now_add=True)

    stake_request = models.ForeignKey(StakeRequest, on_delete=models.CASCADE)

    group_id = get_group_id_field()
    revenue = models.DecimalField()

    class Meta:
        unique_together = ('created', 'stake_request')
