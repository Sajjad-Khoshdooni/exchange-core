import logging
import random
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from accounts.models import Notification, Account, TrafficSource
from ledger.models import Prize, Asset
from ledger.utils.external_price import BUY, get_external_price
from ledger.utils.fields import get_amount_field, get_created_field
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)


class MissionJourney(models.Model):
    SHIB, VOUCHER = 'true', 'voucher'

    name = models.CharField(max_length=64)
    active = models.BooleanField(default=False)
    promotion = models.CharField(max_length=8, unique=True, choices=((SHIB, SHIB), (VOUCHER, VOUCHER)))

    default = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @classmethod
    def get_journey(cls, account: Account) -> 'MissionJourney':
        journey = MissionJourney.objects.filter(promotion=account.user.promotion, active=True).first()
        if not journey:
            default_journey = MissionJourney.objects.filter(active=True, default=True).first()
            return default_journey
        else:
            return journey

    def get_active_mission(self, account: Account):
        for mission in self.missiontemplate_set.filter(active=True):
            if not mission.finished(account):
                return mission


class MissionTemplate(models.Model):
    journey = models.ForeignKey(MissionJourney, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)
    expiration = models.DateTimeField(null=True, blank=True, db_index=True)

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
    NORMAL, MYSTERY_BOX = 'normal', 'mystery_box'

    mission = models.OneToOneField(MissionTemplate, on_delete=models.CASCADE)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, null=True, blank=True)
    amount = get_amount_field()
    voucher = models.BooleanField(default=False)

    @property
    def type(self):
        if self.asset:
            return self.NORMAL
        else:
            return self.MYSTERY_BOX

    def get_prize_achievement_message(self, prize: Prize):

        if not self.asset:
            template = 'جعبه شانس به شما تعلق گرفت. برای دریافت آن، کلیک کنید.'
        elif not self.voucher:
            template = 'جایزه {amount} {symbol} به شما تعلق گرفت. برای دریافت، کلیک کنید.'.format(
                amount=humanize_number(prize.asset.get_presentation_amount(prize.amount)),
                symbol=self.asset.name_fa
            )
        else:
            template = 'جایزه تخفیف کارمزد تا سقف {amount} {symbol} به شما تعلق گرفت. برای دریافت، کلیک کنید.'.format(
                amount=humanize_number(prize.asset.get_presentation_amount(prize.amount)),
                symbol=self.asset.name_fa
            )

        return template

    def achieved(self, account: Account):
        return Prize.objects.filter(account=account, achievement=self).exists()

    def get_mystery_prize(self):
        rand = random.randint(1, 100)

        if rand <= 1:
            return {'coin': 'PEPE', 'amount': 2_000_000}
        elif rand <= 6:
            return {'coin': 'SHIB', 'amount': 100_000}
        elif rand <= 41:
            return {'coin': 'LUNC', 'amount': 2000}
        else:
            return {'coin': 'USDT', 'amount': 10, 'voucher': True}

    def achieve_prize(self, account: Account):
        value = 0

        voucher_expiration = None

        asset = self.asset
        amount = self.amount
        voucher = self.voucher
        auto_redeem = voucher

        if voucher:
            voucher_expiration = timezone.now() + timedelta(days=30)

        if not asset:
            mystery = self.get_mystery_prize()
            asset = Asset.objects.get(symbol=mystery['coin'])
            amount = mystery['amount']
            voucher = mystery.get('voucher', False)
            auto_redeem = False

            if voucher:
                voucher_expiration = timezone.now() + timedelta(days=7)

        if not voucher:
            price = get_external_price(Asset.SHIB, base_coin=Asset.USDT, side=BUY, allow_stale=True) or 0
            value = amount * price

        with WalletPipeline() as pipeline:
            prize, created = Prize.objects.get_or_create(
                account=account,
                achievement=self,
                defaults={
                    'amount': amount,
                    'asset': asset,
                    'value': value,
                    'voucher_expiration': voucher_expiration
                }
            )

            if auto_redeem:
                prize.build_trx(pipeline)

            if created:
                title = 'دریافت جایزه'

                Notification.send(
                    recipient=account.user,
                    title=title,
                    message=self.get_prize_achievement_message(prize),
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
    WEEKLY_TRADE = 'weekly_trade'
    REFERRAL = 'referral'
    SET_EMAIL = 'set_email'

    SCOPE_CHOICES = ((VERIFY_LEVEL2, VERIFY_LEVEL2), (DEPOSIT, DEPOSIT), (TRADE, TRADE), (REFERRAL, REFERRAL),
                    (SET_EMAIL, SET_EMAIL), (WEEKLY_TRADE, WEEKLY_TRADE))

    BOOL, NUMBER = 'bool', 'number'

    mission = models.ForeignKey(MissionTemplate, on_delete=models.CASCADE)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)

    order = models.PositiveSmallIntegerField(default=0)
    type = models.CharField(max_length=8, default=NUMBER, choices=((BOOL, BOOL), (NUMBER, NUMBER)))
    max = models.PositiveIntegerField(default=1)

    title = models.CharField(max_length=32)
    link = models.CharField(max_length=32)
    app_link = models.CharField(max_length=256, default='')
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

    def __str__(self):
        return '%s / %s' % (self.mission.name, self.type)


class UserMission(models.Model):
    created = get_created_field()
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    mission = models.ForeignKey(MissionTemplate, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'mission')
