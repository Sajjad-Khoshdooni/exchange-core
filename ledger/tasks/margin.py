from decimal import Decimal

from celery import shared_task

from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.margin import MARGIN_CALL_ML_THRESHOLD, LIQUIDATION_ML_THRESHOLD
from ledger.utils.margin import MarginInfo


def warn_risky_level(account: Account, margin_level: Decimal):
    pass


def liquid(account: Account, margin_level: Decimal):
    pass


@shared_task()
def check_margin_level():
    margin_accounts = set(Wallet.objects.filter(market=Wallet.MARGIN).values_list('account', flat=True))
    accounts = Account.objects.filter(id__in=margin_accounts)

    for account in accounts:
        info = MarginInfo.get(account)
        margin_level = info.get_margin_level()

        if margin_level <= LIQUIDATION_ML_THRESHOLD:
            liquid(account, margin_level)

        if margin_level <= MARGIN_CALL_ML_THRESHOLD:
            warn_risky_level(account, margin_level)
