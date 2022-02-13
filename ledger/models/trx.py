from decimal import Decimal
from typing import Union
from uuid import uuid4

from django.db import models

from ledger.models import Wallet
from ledger.utils.fields import get_amount_field


class Trx(models.Model):
    TRADE = 't'
    TRANSFER = 'f'
    MARGIN_TRANSFER = 'm'
    MARGIN_BORROW = 'b'
    LIQUID = 'l'
    COMMISSION = 'c'

    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    scope = models.CharField(
        max_length=1,
        choices=((TRADE, 'trade'), (TRANSFER, 'transfer'), (MARGIN_TRANSFER, 'margin transfer'),
                 (MARGIN_BORROW, 'margin borrow'), (COMMISSION, 'commission'))
    )

    class Meta:
        unique_together = ('group_id', 'sender', 'receiver', 'scope')

    def save(self, *args, **kwargs):
        assert self.sender.asset == self.receiver.asset
        assert self.sender != self.receiver
        assert self.amount > 0

        return super(Trx, self).save(*args, **kwargs)

    @classmethod
    def transaction(
            cls,
            sender: Wallet,
            receiver: Wallet,
            amount: Union[Decimal, int],
            scope: str,
            group_id: str
    ):
        trx, _ = Trx.objects.get_or_create(
            sender=sender,
            receiver=receiver,
            scope=scope,
            group_id=group_id,
            defaults={
                'amount': amount
            }
        )

        return trx
