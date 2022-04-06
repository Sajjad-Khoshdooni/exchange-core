import logging
from uuid import uuid4

from django.db import models

from accounts.models import Account, User, Notification
from ledger.models import Trx, Asset
from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


class Prize(models.Model):
    SIGN_UP_PRIZE_ACTIVATE = False

    SIGN_UP_PRIZE, SIGN_UP_PRIZE_AMOUNT = 'sign up', 1000
    LEVEL2_PRIZE, LEVEL2_PRIZE_AMOUNT = 'level 2 verification', 2000
    FIRST_TRADE_PRIZE, FIRST_TRADE_PRIZE_AMOUNT = 'first trade', 3000

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(to=Account, on_delete=models.CASCADE, verbose_name='کاربر')
    amount = get_amount_field()
    scope = models.CharField(
        max_length=25,
        choices=(
            (LEVEL2_PRIZE, LEVEL2_PRIZE), (SIGN_UP_PRIZE, SIGN_UP_PRIZE), (FIRST_TRADE_PRIZE, FIRST_TRADE_PRIZE)
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

    def __str__(self):
        return 'a'


def alert_user_prize(user: User, scope: str):
    from ledger.models import Prize
    from ledger.utils.precision import humanize_number
    level = Notification.SUCCESS

    if scope == Prize.SIGN_UP_PRIZE:
        title = '{} شیبا به کیف پول شما اضافه شد.'.format(humanize_number(Prize.SIGN_UP_PRIZE_AMOUNT))
    elif scope == Prize.LEVEL2_PRIZE:
        title = '{} شیبا به کیف پول شما اضافه شد.'.format(humanize_number(Prize.LEVEL2_PRIZE_AMOUNT))
    elif scope == Prize.FIRST_TRADE_PRIZE:
        title = '{} شیبا به کیف پول شما اضافه شد.'.format(humanize_number(Prize.FIRST_TRADE_PRIZE_AMOUNT))
    else:
        logger.warning('unhandled scope received', extra={'scope': scope})
        return

    Notification.send(
        recipient=user,
        title=title,
        level=level
    )