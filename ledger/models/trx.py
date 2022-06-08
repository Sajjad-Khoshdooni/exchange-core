import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Union
from uuid import uuid4, UUID

from django.db import models, transaction
from django.db.models import F

from ledger.models import Wallet
from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


@dataclass
class FakeTrx:
    sender: Wallet
    receiver: Wallet
    amount: int = 0
    group_id: str = '00000000-0000-0000-0000-000000000000'

    def save(self):
        logger.info('ignoring saving null trx')

    @classmethod
    def from_trx(cls, trx: 'Trx') -> 'FakeTrx':
        if isinstance(trx, FakeTrx):
            return trx

        return FakeTrx(sender=trx.sender, receiver=trx.receiver, amount=trx.amount)


class Trx(models.Model):
    TRADE = 't'
    TRANSFER = 'f'
    MARGIN_TRANSFER = 'm'
    MARGIN_BORROW = 'b'
    FAST_LIQUID = 'fl'
    LIQUID = 'l'
    COMMISSION = 'c'
    PRIZE = 'p'
    REVERT = 'r'

    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    scope = models.CharField(
        max_length=2,
        choices=((TRADE, 'trade'), (TRANSFER, 'transfer'), (MARGIN_TRANSFER, 'margin transfer'),
                 (MARGIN_BORROW, 'margin borrow'), (COMMISSION, 'commission'), (LIQUID, 'liquid'),
                 (FAST_LIQUID, 'fast liquid'), (PRIZE, 'prize'), (REVERT, 'revert'))
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
            group_id: Union[str, UUID],
    ):
        assert amount >= 0

        if amount == 0 or sender == receiver:
            return FakeTrx(
                sender=sender,
                receiver=receiver
            )

        with transaction.atomic():
            trx, created = Trx.objects.get_or_create(
                sender=sender,
                receiver=receiver,
                scope=scope,
                group_id=group_id,
                defaults={
                    'amount': amount
                }
            )

            if created:
                Wallet.objects.filter(id=sender.id).update(balance=F('balance') - amount)
                Wallet.objects.filter(id=receiver.id).update(balance=F('balance') + amount)

                sender.balance -= amount
                receiver.balance += amount

        return trx

    def revert(self):
        group_id = uuid4()

        return self.transaction(
            sender=self.receiver,
            receiver=self.sender,
            amount=self.amount,
            scope=self.REVERT,
            group_id=group_id
        )
