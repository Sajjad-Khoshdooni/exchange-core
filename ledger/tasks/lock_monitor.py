from celery import shared_task
from datetime import timedelta
from django.utils import timezone
from ledger.models import BalanceLock

#
def lock_monitor():
    five_min_ago = timezone.now() - timedelta(minutes=5)
    amount = BalanceLock.objects.filter(created__lte=five_min_ago, freed=False).count()
