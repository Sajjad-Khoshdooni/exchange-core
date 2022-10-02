from django.db import models

from accounts.models import Notification, Account
from ledger.models import Prize, Asset


class MissionJourney(models.Model):
    name = models.CharField(max_length=64)
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @classmethod
    def get_journey(cls, account: Account) -> 'MissionJourney':
        return MissionJourney.objects.filter(active=True).first()

    def get_active_mission(self, account: Account):
        for mission in self.mission_set.all():
            if not mission.finished(account):
                return mission


class Mission(models.Model):
    journey = models.ForeignKey(MissionJourney, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    order = models.PositiveSmallIntegerField(default=0)

    def achievable(self, account: Account):
        if not self.achievement.achieved(account):
            return self.finished(account)

    def finished(self, account: Account):
        return all([task.finished(account) for task in self.task_set.all()])

    class Meta:
        ordering = ('order', )


class Achievement(models.Model):
    mission = models.OneToOneField(Mission, on_delete=models.CASCADE)
    scope = models.CharField(max_length=32, choices=Prize.PRIZE_CHOICES)

    def achieved(self, account: Account):
        return Prize.objects.filter(account=account, scope=self.scope).exists()

    def get_asset(self) -> Asset:
        return Asset.get(Asset.SHIB)


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
    order = models.PositiveSmallIntegerField(default=0)
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
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
