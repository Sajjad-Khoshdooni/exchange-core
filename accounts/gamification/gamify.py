from accounts.models import Account, User
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

    def __init__(self, account: Account):
        self.account = account

    def get_progress(self):
        raise NotImplementedError

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
            'link': self.link
        }

        return data


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
            'amount': Prize.TRADE_2M_AMOUNT,
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


class Trade2MCondition(Condition):
    type = Condition.NUMBER
    max = 2_000_000
    name = 'trade_2m'
    title = 'معامله'
    link = 'به ارزش ۲ میلیون تومان معامله کنید و ۵۰,۰۰۰ شیبا جایزه بگیرید.'
    description = '/trade/classic/BTCUSDT'

    def get_progress(self):
        return self.account.trade_volume_irt


condition_groups = [
    ConditionGroup(
        conditions=[
            VerifyLevel2Condition, DepositCondition, Trade2MCondition
        ],
        achievements=[
            PrizeAchievement(Prize.TRADE_2M_PRIZE)
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
