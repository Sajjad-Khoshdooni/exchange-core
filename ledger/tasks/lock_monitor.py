from celery import shared_task
from datetime import timedelta
from django.utils import timezone

from accounts.utils.admin import url_to_admin_list
from accounts.utils.telegram import send_system_message
from ledger.models import BalanceLock


@shared_task(queue='celery')
def lock_monitor():
    five_min_ago = timezone.now() - timedelta(minutes=5)
    balance_lock_count = BalanceLock.objects.filter(created__lte=five_min_ago, freed=False).count()
    if balance_lock_count > 0:
        link = url_to_admin_list(BalanceLock) + '?freed__exact=0'
        send_system_message(
            message='Non freed locks exists {}'.format(balance_lock_count), link=link
        )
    return

