from django.db.models import Sum

from accounts.models import Account, User
from financial.models import Payment, PaymentRequest
from gamify.models import Task
from ledger.models import Transfer
from ledger.utils.fields import DONE


class BaseGoalType:
    name = ''

    def __init__(self, task):
        self.task = task

    def get_progress(self, account: Account):
        raise NotImplementedError


class VerifyLevel2Goal(BaseGoalType):
    name = Task.VERIFY_LEVEL2

    def get_progress(self, account: Account):
        return account.user.level > User.LEVEL1


class DepositGoal(BaseGoalType):
    name = Task.DEPOSIT

    def get_progress(self, account: Account):
        fiat_deposit = PaymentRequest.objects.filter(
            payment__status=DONE,
            bank_card__user=account.user
        ).aggregate(sum=Sum('amount'))['sum'] or 0

        if fiat_deposit >= self.task.max:
            return fiat_deposit

        crypto_deposit = Transfer.objects.filter(
            wallet__account=account,
            deposit=True,
            status=DONE
        ).aggregate(sum=Sum('irt_value'))['sum'] or 0

        return fiat_deposit + crypto_deposit


class TradeGoal(BaseGoalType):
    name = Task.TRADE

    def get_progress(self, account: Account):
        return account.trade_volume_irt


class ReferralGoal(BaseGoalType):
    name = Task.REFERRAL

    def get_progress(self, account: Account):
        return account.get_invited_count()


class SetEmailGoal(BaseGoalType):
    name = Task.SET_EMAIL

    def get_progress(self, account: Account):
        return bool(account.user.email)


GOAL_TYPES = [VerifyLevel2Goal, DepositGoal, TradeGoal, ReferralGoal, SetEmailGoal]
