from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounting.models import TradeRevenue
from analytics.models import DailyAnalytics


@shared_task(queue='history')
def create_analytics():
    now = timezone.now()
    start = now - timedelta(days=30)

    accounts = set(TradeRevenue.objects.filter(
        created__range=(start, now)
    ).values_list('account', flat=True).distinct())

    old_accounts = set(TradeRevenue.objects.filter(
        created__range=(start - timedelta(days=1), now - timedelta(days=1))
    ).values_list('account', flat=True).distinct())

    DailyAnalytics.objects.get_or_create(
        created=now,
        defaults={
            'active_30': len(accounts),
            'churn_30': len(old_accounts - accounts),
            'new_30': len(accounts - old_accounts),
        }
    )
