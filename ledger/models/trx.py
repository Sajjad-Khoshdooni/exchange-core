import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Union
from uuid import uuid4, UUID

from django.db import models, transaction
from django.db.models import F, CheckConstraint, Q

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
    AIRDROP = 'ad'

    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    scope = models.CharField(
        max_length=2,
        choices=((TRADE, 'trade'), (TRANSFER, 'transfer'), (MARGIN_TRANSFER, 'margin transfer'),
                 (MARGIN_BORROW, 'margin borrow'), (COMMISSION, 'commission'), (LIQUID, 'liquid'),
                 (FAST_LIQUID, 'fast liquid'), (PRIZE, 'prize'), (REVERT, 'revert'), (AIRDROP, 'airdrop'))
    )

    class Meta:
        unique_together = ('group_id', 'sender', 'receiver', 'scope')
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_trx_amount', ), ]

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
            fake_trx: bool = False
    ):
        assert amount >= 0

        if amount == 0 or sender == receiver or fake_trx:
            return FakeTrx(
                sender=sender,
                receiver=receiver,
                amount=amount,
                group_id=group_id
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
                wallet_changes = [
                    (sender.id, F('balance') - amount),
                    (receiver.id, F('balance') + amount),
                ]

                wallet_changes.sort(key=lambda w: w[0])

                for wallet_id, balance_change in wallet_changes:
                    Wallet.objects.filter(id=wallet_id).update(balance=balance_change)

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
