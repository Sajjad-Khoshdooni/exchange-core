from accounts.models import Account, User, Notification
from ledger.models import Transfer, Prize


class Condition:

    BOOL, NUMBER = 'bool', 'number'

    type = NUMBER

    name = None
    max = None
    title = None
    link = ''
    description = ''
    cta_title = ''
    alert_level = Notification.WARNING

    def __init__(self, account: Account):
        self.account = account

    def get_progress(self):
        raise NotImplementedError

    def finished(self):
        return self.get_progress_percent() == 100

    def get_progress_percent(self) -> int:
        _progress = self.get_progress()

        if self.type == self.BOOL:
            if _progress:
                return 100
            else:
                return 0
        else:
            return max(min(int(_progress / self.max * 100), 100), 0)

    def as_dict(self):
        progress = self.get_progress_percent()

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

    def get_alert_dict(self):
        return {
            'text': self.description,
            'btn_link': self.link,
            'btn_title': self.title,
            'level': self.alert_level
        }


class Achievement:

    def achieved(self, account: Account):
        raise NotImplementedError

    def as_dict(self):
        raise NotImplementedError


class PrizeAchievement(Achievement):
    def __init__(self, scope: str):
        self.scope = scope

    def as_dict(self):
        return {
            'type': 'prize',
            'scope': self.scope,
            'amount': Prize.PRIZE_AMOUNTS[self.scope],
            'asset': 'SHIB',
        }

    def achieved(self, account: Account):
        return Prize.objects.filter(account=account, scope=self.scope).exists()


class ConditionGroup:
    def __init__(self, conditions: list, achievements: list):
        self.conditions = conditions
        self.achievements = achievements

    def as_dict(self, account: Account):
        items = [
            c(account).as_dict() for c in self.conditions
        ]

        return {
            'goals': items,
            'achievements': [
                {
                    **a.as_dict(),
                    'achieved': a.achieved(account)
                } for a in self.achievements
            ],
            'finished': all(map(lambda i: i['finished'], items))
        }


class VerifyLevel2Condition(Condition):
    type = Condition.BOOL
    name = 'verify_level2'
    title = 'احراز هویت'
    link = '/account/verification/basic'
    description = 'با تکمیل احراز هویت، بدون محدودیت در راستین خرید و فروش کنید.'

    def get_progress(self):
        return self.account.user.level > User.LEVEL1


class DepositCondition(Condition):
    type = Condition.BOOL
    name = 'deposit'
    title = 'واریز'
    link = '/wallet/spot/money-deposit'
    description = 'با واریز وجه، تنها چند ثانیه با خرید و فروش رمزارز فاصله دارید.'

    def get_progress(self):
        return Transfer.objects.filter(wallet__account=self.account, deposit=True) or \
               self.account.user.first_fiat_deposit_date


class TradeStep1Condition(Condition):
    type = Condition.NUMBER
    max = Prize.TRADE_THRESHOLD_STEP1
    name = Prize.TRADE_PRIZE_STEP1
    title = 'معامله'
    link = '/trade/classic/BTCUSDT'
    description = 'به ارزش ۲ میلیون تومان معامله کنید و ۵۰,۰۰۰ شیبا جایزه بگیرید.'

    def get_progress(self):
        return self.account.trade_volume_irt


class TradeStep2Condition(Condition):
    type = Condition.NUMBER
    max = Prize.TRADE_THRESHOLD_STEP2
    name = Prize.TRADE_PRIZE_STEP2
    title = 'معامله'
    link = '/trade/classic/BTCUSDT'
    description = 'به ارزش ۲۰ میلیون تومان معامله کنید و ۱۰۰,۰۰۰ شیبا جایزه بگیرید.'

    def get_progress(self):
        return self.account.trade_volume_irt


class InviteCondition(Condition):
    type = Condition.NUMBER
    max = 5
    name = 'invite'
    title = 'دعوت از دوستان'
    link = '/account/referral'
    description = 'دوستان خود را به راستین دعوت کنید و از معامله‌آن‌ها درآمدزایی کنید.'

    def get_progress(self):
        return self.account.get_invited_count()


condition_groups = [
    ConditionGroup(
        conditions=[
            VerifyLevel2Condition, DepositCondition, TradeStep1Condition
        ],
        achievements=[
            PrizeAchievement(Prize.TRADE_PRIZE_STEP1)
        ]
    ),
    ConditionGroup(
        conditions=[
            TradeStep2Condition, InviteCondition
        ],
        achievements=[
            PrizeAchievement(Prize.TRADE_PRIZE_STEP2)
        ]
    )
]


def get_groups_data(account, only_active=False):
    groups = []

    activated = False

    for group in condition_groups:
        data = group.as_dict(account)

        data['active'] = not data['finished'] and not activated

        if data['active']:
            activated = True

            if only_active:
                return data

        groups.append(data)

    return groups
