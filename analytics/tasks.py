from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.models import TradeRevenue
from analytics.models import ActiveTrader


@shared_task(queue='history')
def create_analytics():
    now = timezone.now()

    for period in ActiveTrader.PERIODS:
        start = now - timedelta(days=period)

        accounts = set(TradeRevenue.objects.filter(
            created__range=(start, now)
        ).values_list('account', flat=True).distinct())

        old_accounts = set(TradeRevenue.objects.filter(
            created__range=(start - timedelta(days=1), now - timedelta(days=1))
        ).values_list('account', flat=True).distinct())

        ActiveTrader.objects.get_or_create(
            created=now,
            period=period,
            defaults={
                'active': len(accounts),
                'churn': len(old_accounts - accounts),
                'new': len(accounts - old_accounts),
            }
        )
