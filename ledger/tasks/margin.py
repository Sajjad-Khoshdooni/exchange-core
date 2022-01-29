import logging

from celery import shared_task

from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.liquidation import LiquidationEngine
from ledger.utils.margin import MARGIN_CALL_ML_THRESHOLD, LIQUIDATION_ML_THRESHOLD
from ledger.utils.margin import MarginInfo

logger = logging.getLogger(__name__)


@shared_task()
def check_margin_level():
    margin_accounts = set(Wallet.objects.filter(market=Wallet.MARGIN).values_list('account', flat=True))
    accounts = Account.objects.filter(id__in=margin_accounts)

    for account in accounts:
        margin_info = MarginInfo.get(account)
        margin_level = margin_info.get_margin_level()

        if margin_level <= LIQUIDATION_ML_THRESHOLD:
            engine = LiquidationEngine(account, margin_info)
            engine.start()

        if margin_level <= MARGIN_CALL_ML_THRESHOLD:
            logger.warning('Send MARGIN_CALL_ML_THRESHOLD for account = %d' % account.id)
            # warn_risky_level(account, margin_level)
