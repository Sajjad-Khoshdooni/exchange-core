import logging
from datetime import timedelta
from uuid import uuid4

from django.db import models
from django.db.models import CheckConstraint, Q

from accounts.models import Account
from ledger.models import Trx, Asset, Wallet
from ledger.utils.fields import get_amount_field
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class Prize(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    achievement = models.ForeignKey('gamify.Achievement', on_delete=models.CASCADE)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    group_id = models.UUIDField(default=uuid4, db_index=True)

    amount = get_amount_field()
    asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE)
    redeemed = models.BooleanField(default=False)

    fake = models.BooleanField(default=False)
    variant = models.CharField(null=True, blank=True, max_length=16)
    value = get_amount_field()

    class Meta:
        unique_together = [('account', 'achievement', 'variant')]
        constraints = [CheckConstraint(check=Q(amount__gte=0), name='check_ledger_prize_amount', ), ]

    def build_trx(self, pipeline: WalletPipeline):
        if self.redeemed:
            logger.info('Ignored redeem prize because it is redeemed before.')
            return

        self.redeemed = True
        self.save(update_fields=['redeemed'])

        system = Account.system()

        if self.achievement.voucher:
            market = Wallet.VOUCHER
            expiration = self.account.user.date_joined + timedelta(days=30)
        else:
            market = Wallet.SPOT
            expiration = None

        pipeline.new_trx(
            group_id=self.group_id,
            sender=self.asset.get_wallet(system),
            receiver=self.asset.get_wallet(self.account, market=market, expiration=expiration),
            amount=self.amount,
            scope=Trx.PRIZE
        )

    def __str__(self):
        return '%s %s %s' % (self.account, self.amount, self.asset)
