import logging
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q

from accounts.models import Account
from ledger.models import Trx, Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class Prize(models.Model):
    VERIFY_PRIZE = 'level2_verify'
    TRADE_PRIZE_STEP1 = 'trade_2m'
    TRADE_PRIZE_STEP2 = 'trade_s2'
    REFERRAL_TRADE_2M_PRIZE = 'referral_trade_2m'

    PRIZE_CHOICES = (
        (VERIFY_PRIZE, VERIFY_PRIZE),
        (TRADE_PRIZE_STEP1, TRADE_PRIZE_STEP1),
        (TRADE_PRIZE_STEP2, TRADE_PRIZE_STEP2),
        (REFERRAL_TRADE_2M_PRIZE, REFERRAL_TRADE_2M_PRIZE)
    )

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    amount = get_amount_field()
    asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE)
    group_id = models.UUIDField(default=uuid4, db_index=True)
    fake = models.BooleanField(default=False)

    redeemed = models.BooleanField(default=False)

    variant = models.CharField(null=True, blank=True, max_length=16)

    value = get_amount_field()

    class Meta:
        unique_together = [('account', 'scope', 'variant')]
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_prize_amount', ), ]

    def build_trx(self, pipeline: WalletPipeline):
        if self.redeemed:
            logger.info('Ignored redeem prize because it is redeemed before.')
            return

        self.redeemed = True
        self.save(update_fields=['redeemed'])

        system = Account.system()
        pipeline.new_trx(
            group_id=self.group_id,
            sender=self.asset.get_wallet(system),
            receiver=self.asset.get_wallet(self.account),
            amount=self.amount,
            scope=Trx.PRIZE
        )

    def __str__(self):
        return '%s %s %s' % (self.account, self.amount, self.asset)
