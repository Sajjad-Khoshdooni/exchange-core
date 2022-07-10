import uuid
from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.utils.fields import get_group_id_field
from stake.models import StakeOption


class StakeRequest(models.Model):

    PROCESS, PENDING, DONE = 'process', 'pending', ' done'
    CANCEL_PROCESS, CANSEL_PENDING, CANSEL_CANSEL = 'cancel_process', 'cancel_pending', 'cancel_cancel'

    status_choice = ((PROCESS, PROCESS), (PENDING, PENDING), (DONE, DONE), (CANCEL_PROCESS, CANCEL_PROCESS),
                     (CANSEL_PENDING, CANSEL_PENDING), (CANSEL_CANSEL, CANSEL_CANSEL))

    status = models.CharField(choices=status_choice, max_length=16, default=PROCESS)

    stake_option = models.ForeignKey(StakeOption, on_delete=models.CASCADE)

    amount = models.PositiveIntegerField()

    group_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
    )

    account = models.ForeignKey(Account, on_delete=models.CASCADE)

