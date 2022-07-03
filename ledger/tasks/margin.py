import logging
from decimal import Decimal

from celery import shared_task

from accounts.models import Account, Notification
from accounts.tasks import send_message_by_kavenegar
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from ledger.margin.margin_info import MARGIN_CALL_ML_THRESHOLD, LIQUIDATION_ML_THRESHOLD, \
    MARGIN_CALL_ML_ALERTING_RESOLVE_THRESHOLD
from ledger.margin.margin_info import MarginInfo
from ledger.models import Wallet
from ledger.models.margin import CloseRequest

logger = logging.getLogger(__name__)


@shared_task(queue='margin')
def check_margin_level():
    margin_accounts = set(Wallet.objects.filter(market=Wallet.LOAN, balance__lt=0).values_list('account', flat=True))
    accounts = Account.objects.filter(id__in=margin_accounts, user__isnull=False)

    status = 0

    for account in accounts:
        margin_info = MarginInfo.get(account)
        margin_level = margin_info.get_margin_level()

        logger.info('margin_level for account=%d is %s' % (account.id, margin_level))

        if margin_level <= LIQUIDATION_ML_THRESHOLD:
            CloseRequest.close_margin(account, reason=CloseRequest.LIQUIDATION)
            status = 2

        elif not account.margin_alerting and margin_level <= MARGIN_CALL_ML_THRESHOLD:
            logger.warning('Send MARGIN_CALL_ML_THRESHOLD for account = %d' % account.id)
            warn_risky_level(account, margin_level)

            if status == 0:
                status = 1

            Account.objects.filter(id=account.id).update(margin_alerting=True)

        elif margin_level > MARGIN_CALL_ML_ALERTING_RESOLVE_THRESHOLD:
            Account.objects.filter(id=account.id).update(margin_alerting=False)

    return status


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

    send_message_by_kavenegar(
        phone=user.phone,
        template='alert-margin-liquidation',
        token='تعهدی'
    )
