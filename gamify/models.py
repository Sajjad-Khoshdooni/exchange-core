import logging

from django.db import models

from accounts.models import Notification, Account
from ledger.models import Prize, Asset
from ledger.utils.fields import get_amount_field

logger = logging.getLogger(__name__)


class MissionJourney(models.Model):
    name = models.CharField(max_length=64)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @classmethod
    def get_journey(cls, account: Account) -> 'MissionJourney':
        return MissionJourney.objects.filter(active=True).first()

    def get_active_mission(self, account: Account):
        for mission in self.mission_set.filter(active=True):
            if not mission.finished(account):
                return mission

    def achieve_if_can(self, account: Account, task_scope: str):
        try:
            missions = self.mission_set.filter(active=True, task__scope=task_scope)

            for mission in missions:
                if mission.achievable(account):
                    mission.achievement.achieved(account)

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
        for task in self.task_set:
            if not task.finished(account):
                return task

    class Meta:
        ordering = ('order', )

    def __str__(self):
        return self.name


class Achievement(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE)
    scope = models.CharField(max_length=32, choices=Prize.PRIZE_CHOICES)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE)
    amount = get_amount_field()
    voucher = models.BooleanField(default=False)

    def achieved(self, account: Account):
        return Prize.objects.filter(account=account, scope=self.scope).exists()

    def __str__(self):
        return dict(Prize.PRIZE_CHOICES)[self.scope]


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
    description = models.CharField(max_length=64)
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
