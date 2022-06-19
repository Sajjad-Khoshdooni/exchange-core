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
    amount: Decimal = 0
    group_id: Union[str,UUID] = '00000000-0000-0000-0000-000000000000'
    scope: str = ''

    def save(self):
        logger.info('ignoring saving null trx')

    @classmethod
    def from_trx(cls, trx: 'Trx') -> 'FakeTrx':
        if isinstance(trx, FakeTrx):
            return trx

        return FakeTrx(sender=trx.sender, receiver=trx.receiver, amount=trx.amount)

    def to_trx(self) -> 'Trx':
        return Trx(sender=self.sender, receiver=self.receiver, amount=self.amount, group_id=self.group_id, scope=self.scope)


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
    ) -> FakeTrx:
        assert amount >= 0

        if amount != 0 and sender != receiver and not fake_trx:
            from ledger.utils.wallet_update_manager import WalletUpdateManager
            updater = WalletUpdateManager.get_active_or_instant()
            updater.new_trx(sender=sender, receiver=receiver, amount=amount, scope=scope, group_id=group_id)

            sender.balance -= amount
            receiver.balance += amount

        return FakeTrx(
            sender=sender,
            receiver=receiver,
            amount=amount,
            group_id=group_id
        )

    def revert(self):
        group_id = uuid4()

        return self.transaction(
            sender=self.receiver,
            receiver=self.sender,
            amount=self.amount,
            scope=self.REVERT,
            group_id=group_id
        )
