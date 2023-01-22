import logging
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q

from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


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
    SEIZE = 'sz'
    RESERVE = 'rs'
    STAKE_REVENUE = 'sr'
    STAKE = 'st'
    FIX = 'fx'
    STAKE_FEE = 'sf'
    CLOSE_MARGIN = 'cm'
    DEBT_CLEAR = 'dc'

    created = models.DateTimeField(auto_now_add=True)

    sender = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='sent_trx')
    receiver = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='received_trx')
    amount = get_amount_field()

    group_id = models.UUIDField(default=uuid4, db_index=True)

    scope = models.CharField(
        max_length=2,
        choices=((TRADE, 'trade'), (TRANSFER, 'transfer'), (MARGIN_TRANSFER, 'margin transfer'),
                 (MARGIN_BORROW, 'margin borrow'), (COMMISSION, 'commission'), (LIQUID, 'liquid'),
                 (FAST_LIQUID, 'fast liquid'), (PRIZE, 'prize'), (REVERT, 'revert'), (AIRDROP, 'airdrop'),
                 (STAKE, 'stake'), (STAKE_REVENUE, 'stake revenue'), (STAKE_FEE, 'stake fee'), (RESERVE, 'reserve'))
    )

    class Meta:
        unique_together = ('group_id', 'sender', 'receiver', 'scope')
        constraints = [
            CheckConstraint(check=Q(amount__gt=0), name='check_ledger_trx_amount', ),
        ]

    def save(self, *args, **kwargs):
        assert self.sender.asset == self.receiver.asset
        assert self.sender != self.receiver
        assert self.amount > 0

        return super(Trx, self).save(*args, **kwargs)
