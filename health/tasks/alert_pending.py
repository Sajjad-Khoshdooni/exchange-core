from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.utils.admin import url_to_admin_list
from accounts.utils.telegram import send_system_message
from financial.models import FiatWithdrawRequest
from ledger.models import Transfer, OTCTrade, CloseRequest
from ledger.utils.fields import PENDING


@shared_task(queue='celery')
def alert_pending():
    transfer = Transfer.objects.filter(
        status__in=(Transfer.PENDING, Transfer.PROCESSING),
        created__lt=timezone.now() - timedelta(minutes=30)
    ).count()

    fiat_withdraw = FiatWithdrawRequest.objects.filter(
        status__in=(FiatWithdrawRequest.PENDING, FiatWithdrawRequest.PROCESSING),
        created__lt=timezone.now() - timedelta(hours=10)
    ).count()

    otc_trade = OTCTrade.objects.filter(
        status=OTCTrade.PENDING,
        created__lt=timezone.now() - timedelta(minutes=5)
    ).count()

    margin_close_requests = CloseRequest.objects.filter(
        status=PENDING,
        created__lt=timezone.now() - timedelta(minutes=1)
    ).count()

    message = ''
    link = ''
    if transfer:
        message += f'pending crypto_withdraw:{transfer}\n' + \
                   url_to_admin_list(Transfer) + '?status__in=process,pending\n\n'
    if fiat_withdraw:
        message += f'pending fiat_withdraw : {fiat_withdraw}\n' + \
                   url_to_admin_list(FiatWithdrawRequest) + '?status__in=process,pending\n\n'
    if otc_trade:
        message += f'pending otc_trade: {otc_trade}\n' + \
                   url_to_admin_list(OTCTrade) + '?status__exact=pending\n\n'
    if margin_close_requests:
        message += f'pending margin_close: {margin_close_requests}\n' + \
                   url_to_admin_list(CloseRequest) + '?status__exact=pending'

    send_system_message(message=message, link=link)
