from decimal import Decimal
from uuid import uuid4

from django.db import models, transaction

from ledger.models import OTCRequest
from ledger.utils.fields import get_amount_field


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

    created = models.DateTimeField(auto_now_add=True)
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    amount = get_amount_field()
    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)]
    )

    @classmethod
    def create_trade(cls, otc_request: OTCRequest, amount: Decimal) -> 'OTCTrade':
        otc_trade = OTCTrade.objects.create(
            otc_request=otc_request,
            amount=amount,
        )

        