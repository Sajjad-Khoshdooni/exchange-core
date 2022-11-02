import logging

from django.db import models

from accounts.models import Notification, Account, TrafficSource
from ledger.models import Prize, Asset
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import humanize_number
from ledger.utils.price import get_trading_price_usdt, SELL
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class MissionJourney(models.Model):
    DEFAULT, VOUCHER = 'default', 'voucher'

    name = models.CharField(max_length=64)
    active = models.BooleanField(default=False)
    promotion = models.CharField(max_length=8, unique=True, choices=((DEFAULT, DEFAULT), (VOUCHER, VOUCHER)))

    def __str__(self):
        return self.name

    @classmethod
    def get_journey(cls, account: Account) -> 'MissionJourney':
        journey = MissionJourney.objects.filter(promotion=account.user.promotion, active=True).first()
        if not journey:
            default_journey = MissionJourney.objects.filter(active=True, promotion=cls.DEFAULT).first()
            return default_journey
        else:
            return journey

    def get_active_mission(self, account: Account):
        for mission in self.mission_set.filter(active=True):
            if not mission.finished(account):
                return mission

    def achieve_if_can(self, account: Account, task_scope: str):
        try:
            missions = self.mission_set.filter(active=True, task__scope=task_scope)

            for mission in missions:
                if mission.achievable(account):
                    mission.achievement.achieve_prize(account)

        except Exception as e:
            logger.exception('Failed to check prize achievements', extra={
                'account': account.id,
                'exp': e
            })


class Mission(models.Model):
    journey = models.ForeignKey(MissionJourney, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    def achievable(self, account: Account):
        if not self.achievement.achieved(account):
            return self.finished(account)

    def finished(self, account: Account):
        return all([task.finished(account) for task in self.task_set.all()])

    def get_active_task(self, account: Account) -> 'Task':
        for task in self.task_set.all():
            if not task.finished(account):
                return task

    class Meta:
        ordering = ('order', )

    def __str__(self):
        return self.name


class Achievement(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    voucher = models.BooleanField(default=False)

    def achieved(self, account: Account):
        return Prize.objects.filter(account=account, achievement=self).exists()

    def achieve_prize(self, account: Account):
        price = get_trading_price_usdt(Asset.SHIB, SELL, raw_price=True)

        with WalletPipeline() as pipeline:

            value = 0

            if not self.voucher:
                value = self.amount * price

            prize, created = Prize.objects.get_or_create(
                account=account,
                achievement=self,
                defaults={
                    'amount': self.amount,
                    'asset': self.asset,
                    'value': value
                }
            )

            if created:
                title = 'جایزه به شما تعلق گرفت.'
                description = 'جایزه {} {} به شما تعلق گرفت. برای دریافت جایزه، کلیک کنید.'.format(
                    humanize_number(prize.asset.get_presentation_amount(prize.amount)),
                    self.asset.name_fa
                )

                Notification.send(
                    recipient=account.user,
                    title=title,
                    message=description,
                    level=Notification.SUCCESS,
                    link='/account/tasks'
                )

    def __str__(self):
        kind = ''
        if self.voucher:
            kind = ' voucher'

        return '%s %s %s%s' % (self.mission, int(self.amount), self.asset, kind)


class Task(models.Model):
    VERIFY_LEVEL2 = 'verify_level2'
    DEPOSIT = 'deposit'
    TRADE = 'trade'
    REFERRAL = 'referral'
    SET_EMAIL = 'set_email'

    SCOPE_CHOICES = ((VERIFY_LEVEL2, VERIFY_LEVEL2), (DEPOSIT, DEPOSIT), (TRADE, TRADE), (REFERRAL, REFERRAL),
                    (SET_EMAIL, SET_EMAIL))

    BOOL, NUMBER = 'bool', 'number'

    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)

    order = models.PositiveSmallIntegerField(default=0)
    type = models.CharField(max_length=8, default=NUMBER, choices=((BOOL, BOOL), (NUMBER, NUMBER)))
    max = models.PositiveIntegerField(default=1)

    title = models.CharField(max_length=32)
    link = models.CharField(max_length=32)
    description = models.CharField(max_length=128)
    level = models.CharField(max_length=8, choices=Notification.LEVEL_CHOICES, default=Notification.WARNING)

    def get_goal_type(self):
        from gamify.goal_types import GOAL_TYPES

        for gt in GOAL_TYPES:
            if gt.name == self.scope:
                return gt(self)
        else:
            raise NotImplementedError

    def get_progress_percent(self, account: Account) -> int:
        _progress = self.get_goal_type().get_progress(account)

        if self.type == self.BOOL:
            if _progress:
                return 100
            else:
                return 0
        else:
            return max(min(int(_progress / self.max * 100), 100), 0)

    def finished(self, account: Account):
        return self.get_progress_percent(account) == 100

    class Meta:
        ordering = ('order', )