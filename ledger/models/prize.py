import logging
from uuid import uuid4

from django.db import models, transaction
from django.db.models import Q, Sum

from accounts.models import Account, Notification
from ledger.models import Trx, Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import humanize_number

logger = logging.getLogger(__name__)


class Prize(models.Model):
    TRADE_2M_PRIZE, TRADE_2M_AMOUNT = 'trade_2m', 50_000

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    amount = get_amount_field()
    scope = models.CharField(
        max_length=25,
        choices=(
            (TRADE_2M_PRIZE, TRADE_2M_PRIZE),
        ),
        verbose_name='نوع'
    )
    asset = models.ForeignKey(to=Asset, on_delete=models.CASCADE)
    group_id = models.UUIDField(default=uuid4, db_index=True)

    class Meta:
        unique_together = [('account', 'scope')]

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

    if account.trade_volume_irt >= 2_000_000 and \
            not Prize.objects.filter(account=account, scope=Prize.TRADE_2M_PRIZE).exists():

        with transaction.atomic():
            prize = Prize.objects.create(
                account=account,
                amount=Prize.TRADE_2M_AMOUNT,
                scope=Prize.TRADE_2M_PRIZE,
                asset=Asset.get(Asset.SHIB)
            )
            prize.build_trx()
