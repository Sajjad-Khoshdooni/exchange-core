import uuid

from django.db import models

from ledger.utils.fields import get_group_id_field
from stake.models import StakeRequest


class StakeRevenue(models.Model):
    created = models.DateField(auto_now_add=True)

    stake_request = models.ForeignKey(StakeRequest, on_delete=models.CASCADE)

    group_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    revenue = models.DecimalField(max_digits=12, decimal_places=6)

    class Meta:
        unique_together = ('created', 'stake_request')
