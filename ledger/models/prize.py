import logging
from uuid import uuid4

from django.db import models, transaction

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

    variant = models.CharField(null=True, blank=True, max_length=16)

    class Meta:
        unique_together = [('account', 'scope', 'variant')]

    def build_trx(self):
        system = Account.system()
        Trx.transaction(
            group_id=self.group_id,
            sender=self.asset.get_wallet(system),
            receiver=self.asset.get_wallet(self.account),
            amount=self.amount,
            scope=Trx.PRIZE
        )

        title = '{} شیبا به کیف پول شما اضافه شد.'.format(humanize_number(self.amount))

        Notification.send(
            recipient=self.account.user,
            title=title,
            level=Notification.SUCCESS
        )

    def __str__(self):
        return '%s %s %s' % (self.account, self.amount, self.asset)


def check_trade_prize(account: Account):
    account.refresh_from_db()

    if account.trade_volume_irt >= Prize.TRADE_THRESHOLD_STEP1 and \
            not Prize.objects.filter(account=account, scope=Prize.TRADE_PRIZE_STEP1).exists():

        with transaction.atomic():
            prize, created = Prize.objects.get_or_create(
                account=account,
                scope=Prize.TRADE_PRIZE_STEP1,
                defaults={
                    'amount': Prize.PRIZE_AMOUNTS[Prize.TRADE_PRIZE_STEP1],
                    'asset': Asset.get(Asset.SHIB),
                }
            )

            if created:
                prize.build_trx()

                if account.referred_by:
                    prize, created = Prize.objects.get_or_create(
                        account=account.referred_by.owner,
                        scope=Prize.REFERRAL_TRADE_2M_PRIZE,
                        variant=str(account.id),
                        defaults={
                            'amount': Prize.PRIZE_AMOUNTS[Prize.REFERRAL_TRADE_2M_PRIZE],
                            'asset': Asset.get(Asset.SHIB),
                        }
                    )

                    if created:
                        prize.build_trx()
