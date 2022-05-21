import logging
from uuid import uuid4

from django.db import models

from accounts.models import Account, Notification
from ledger.models import Trx, Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import humanize_number

logger = logging.getLogger(__name__)


class Prize(models.Model):
    TRADE_THRESHOLD_STEP1 = 2_000_000
    TRADE_THRESHOLD_STEP2 = 20_000_000

    TRADE_PRIZE_STEP1 = 'trade_2m'
    TRADE_PRIZE_STEP2 = 'trade_s2'
    REFERRAL_TRADE_2M_PRIZE = 'referral_trade_2m'

    PRIZE_AMOUNTS = {
        TRADE_PRIZE_STEP1: 50_000,
        REFERRAL_TRADE_2M_PRIZE: 50_000,
        TRADE_PRIZE_STEP2: 100_000,
    }

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    amount = get_amount_field()
    scope = models.CharField(
        max_length=25,
        choices=(
            (TRADE_PRIZE_STEP1, TRADE_PRIZE_STEP1),
            (REFERRAL_TRADE_2M_PRIZE, REFERRAL_TRADE_2M_PRIZE)
        ),
        verbose_name='نوع'
    )
    asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE)
    group_id = models.UUIDField(default=uuid4, db_index=True)
    fake = models.BooleanField(default=False)

    redeemed = models.BooleanField(default=False)

    variant = models.CharField(null=True, blank=True, max_length=16)

    class Meta:
        unique_together = [('account', 'scope', 'variant')]

    def build_trx(self):
        if self.redeemed:
            logger.info('Ignored redeem prize because it is redeemed before.')
            return

        self.redeemed = True
        self.save(update_fields=['redeem'])

        system = Account.system()
        Trx.transaction(
            group_id=self.group_id,
            sender=self.asset.get_wallet(system),
            receiver=self.asset.get_wallet(self.account),
            amount=self.amount,
            scope=Trx.PRIZE
        )

    def __str__(self):
        return '%s %s %s' % (self.account, self.amount, self.asset)
