from celery import shared_task

from ledger.models import Asset
from provider.models import ProviderOrder


@shared_task(queue='interface')
def auto_hedge_assets():
    for asset in Asset.objects.exclude(hedge_method=Asset.HEDGE_NONE):
        ProviderOrder.try_hedge_for_new_order(asset, ProviderOrder.HEDGE, dry_run=True)
