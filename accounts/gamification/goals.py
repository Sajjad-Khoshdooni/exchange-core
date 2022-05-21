from typing import List

from accounts.models import Account, User
from ledger.models import Transfer, Prize


class Goal:
    BOOL, NUMBER = 'bool', 'number'

    type = NUMBER

    name = None
    max = None
    title = None
    link = ''
    description = ''
    cta_title = ''

    def __init__(self, account: Account):
        self.account = account

    def get_progress(self):
        raise NotImplementedError

    def finished(self):
        progress = self.get_progress()

        if self.type == self.BOOL:
            return progress
        else:
            return progress >= self.max

    def as_dict(self):

        _progress = self.get_progress()

        if self.type == self.BOOL:
            if _progress:
                progress = 100
            else:
                progress = 0
        else:
            progress = max(min(int(_progress / self.max * 100), 100), 0)

        data = {
            'name': self.name,
            'progress': progress,
            'title': self.title,
            'type': self.type,
            'finished': progress == 100,
            'description': self.description,
            'link': self.link,
            'max': self.max,
        }

        return data


class GoalGroup:
    def __init__(self, conditions: list, achievements: list):
        self.conditions = conditions
        self.achievements = achievements

    def as_dict(self, account: Account):
        items = self.get_goals(account)

        return {
            'goals': items,
            'achievements': [
                a(account).as_dict() for a in self.achievements
            ],
            'finished': all(map(lambda i: i['finished'], items))
        }

    def get_goals(self, account: Account) -> List[Goal]:
        return [
            c(account).as_dict() for c in self.conditions
        ]

    def achievable(self, account: Account):
        prize = self.achievements[0]
        if not prize.achieved(account):
            goals = self.get_goals(account)

            return all([g.finished() for g in goals])


class VerifyLevel2Goal(Goal):
    type = Goal.BOOL
    name = 'verify_level2'
    title = 'احراز هویت'
    link = '/account/verification/basic'
    description = 'با تکمیل احراز هویت، بدون محدودیت در راستین خرید و فروش کنید.'

    def get_progress(self):
        return self.account.user.level > User.LEVEL1


class DepositGoal(Goal):
    type = Goal.BOOL
    name = 'deposit'
    title = 'واریز وجه'
    link = '/wallet/spot/money-deposit'
    description = 'با واریز وجه، تنها چند ثانیه با خرید و فروش رمزارز فاصله دارید.'

    def get_progress(self):
        return Transfer.objects.filter(wallet__account=self.account, deposit=True) or \
               self.account.user.first_fiat_deposit_date


class TradeStep1Goal(Goal):
    type = Goal.NUMBER
    max = Prize.TRADE_THRESHOLD_STEP1
    name = Prize.TRADE_PRIZE_STEP1
    title = 'معامله به ارزش ۲ میلیون تومان'
    link = '/trade/classic/BTCUSDT'
    description = 'به ارزش ۲ میلیون تومان معامله کنید و ۵۰,۰۰۰ شیبا جایزه بگیرید.'

    def get_progress(self):
        return self.account.trade_volume_irt


class TradeStep2Goal(Goal):
    type = Goal.NUMBER
    max = Prize.TRADE_THRESHOLD_STEP2
    name = Prize.TRADE_PRIZE_STEP2
    title = 'معامله به ارزش ۲۰ میلیون تومان'
    link = '/trade/classic/BTCUSDT'
    description = 'به ارزش ۲۰ میلیون تومان معامله کنید و ۱۰۰,۰۰۰ شیبا جایزه بگیرید.'

    def get_progress(self):
        return self.account.trade_volume_irt


class InviteGoal(Goal):
    type = Goal.NUMBER
    max = 5
    name = 'invite'
    title = 'دعوت از دوستان'
    link = '/account/referral'
    description = 'دوستان خود را به راستین دعوت کنید و از معامله‌آن‌ها درآمدزایی کنید.'

    def get_progress(self):
        return self.account.get_invited_count()

