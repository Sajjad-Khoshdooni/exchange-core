from accounts.models import Account, User
from ledger.models import Transfer


class Condition:

    BOOL, NUMBER = 'bool', 'number'

    type = NUMBER

    name = None
    max = None
    title = None

    def __init__(self, account: Account):
        self.account = account

    def get_progress(self):
        raise NotImplementedError

    def as_dict(self):
        return {
            'name': self.name,
            'progress': self.get_progress(),
            'max': self.max,
            'title': self.title,
            'type': self.type,
        }


class ConditionGroup:
    def __init__(self, conditions: list, achievements: list):
        self.conditions = conditions
        self.achievements = achievements

    def as_dict(self, account: Account):
        return {
            'items': [
                c(account).as_dict() for c in self.conditions
            ],
            'achievements': [
                a().as_dict() for a in self.achievements
            ]
        }


class PrizeAchievement:
    def __init__(self, symbol: str, amount: int):
        pass

    def as_dict(self):
        return {}


class VerifyLevel2Condition(Condition):
    type = Condition.BOOL
    name = 'verify_level2'
    title = 'احراز هویت'

    def get_progress(self):
        return self.account.user.level > User.LEVEL1


class DepositCondition(Condition):
    type = Condition.BOOL
    name = 'deposit'
    title = 'واریز'

    def get_progress(self):
        return Transfer.objects.filter(wallet__account=self.account, deposit=True) or \
               self.account.user.first_fiat_deposit_date


class Trade2MCondition(Condition):
    type = Condition.NUMBER
    max = 2_000_000
    name = 'trade_2m'
    title = 'معامله'

    def get_progress(self):
        return self.account.trade_volume_irt


condition_groups = [
    ConditionGroup(
        conditions=[
            VerifyLevel2Condition, DepositCondition, Trade2MCondition
        ],
        achievements=[
            # PrizeAchievement(
            #
            # )
        ]
    )
]