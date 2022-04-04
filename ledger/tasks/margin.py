import logging
from decimal import Decimal

from celery import shared_task

from accounts.models import Account, Notification
from accounts.tasks import send_message_by_kavenegar
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from ledger.models import Wallet
from ledger.models.margin import MarginLiquidation
from ledger.utils.liquidation import LiquidationEngine
from ledger.utils.margin import MARGIN_CALL_ML_THRESHOLD, LIQUIDATION_ML_THRESHOLD
from ledger.utils.margin import MarginInfo

logger = logging.getLogger(__name__)


@shared_task(queue='margin')
def check_margin_level():
    margin_accounts = set(Wallet.objects.filter(market=Wallet.MARGIN).values_list('account', flat=True))
    accounts = Account.objects.filter(id__in=margin_accounts, user__isnull=False)

    for account in accounts:
        margin_info = MarginInfo.get(account)
        margin_level = margin_info.get_margin_level()

        if margin_level <= LIQUIDATION_ML_THRESHOLD:
            liquidation = MarginLiquidation.objects.create(
                account=account,
                margin_level=margin_info
            )

            engine = LiquidationEngine(liquidation, margin_info)
            engine.start()

        elif margin_level <= MARGIN_CALL_ML_THRESHOLD:
            logger.warning('Send MARGIN_CALL_ML_THRESHOLD for account = %d' % account.id)
            warn_risky_level(account, margin_level)


def warn_risky_level(account: Account, margin_level: Decimal):
    user = account.user

    Notification.send(
        recipient=user,
        title='حساب تعهدی شما در آستانه‌ی تسویه خودکار است.',
        message='لطفا در اسرع وقت نسبت به افزایش دارایی تتری یا کاهش بدهی‌هایتان اقدام کنید. ',
        level=Notification.ERROR
    )

    link = url_to_edit_object(account)
    send_support_message(
        message='Margin account is going to liquidate. (level = %s)' % round(margin_level, 3),
        link=link
    )

    # send_message_by_kavenegar(
    #     phone=user.phone,
    #     template='liquidation',
    #     token=str(levelup)
    # )

