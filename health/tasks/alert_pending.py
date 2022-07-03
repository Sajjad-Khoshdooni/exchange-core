from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.utils.admin import url_to_admin_list
from accounts.utils.telegram import send_system_message
from financial.models import FiatWithdrawRequest
from ledger.models import Transfer, OTCTrade


@shared_task(queue='celery')
def alert_pending():
    transfer = Transfer.objects.filter(
        status__in=(Transfer.PENDING, Transfer.PROCESSING),
        created__lt=timezone.now() - timedelta(minutes=60)
    ).count()

    fiat_withdraw = FiatWithdrawRequest.objects.filter(
        status__in=(FiatWithdrawRequest.PENDING, FiatWithdrawRequest.PROCESSING),
        created__lt=timezone.now() - timedelta(minutes=60)
    ).count()

    otc_trade = OTCTrade.objects.filter(
        status=OTCTrade.PENDING,
        created__lt=timezone.now() - timedelta(minutes=60)
    ).count()
    message = ''
    link = ''
    if transfer != 0:
        message += 'pending crypto_withdraw:{} \n'.format(transfer) +\
                   url_to_admin_list(Transfer) + '?status__in=process,pending\n\n'
    if fiat_withdraw != 0:
        message += 'pending fiat_withdraw : {} \n'.format(fiat_withdraw) +\
                   url_to_admin_list(FiatWithdrawRequest) + '?status__in=process,pending\n\n'
    if otc_trade != 0:
        message += 'pending otc_trade: {}' + \
                   url_to_admin_list(OTCTrade) + '?status__exact=pending'

    send_system_message(message=message, link=link)


