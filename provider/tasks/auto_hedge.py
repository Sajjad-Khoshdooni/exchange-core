from celery import shared_task

from ledger.models import Asset
from provider.models import ProviderOrder


@shared_task(queue='binance')
def auto_hedge_assets(dry_run: bool = True):
    for asset in Asset.objects.exclude(hedge_method=Asset.HEDGE_NONE, ):
        ProviderOrder.try_hedge_for_new_order(asset, ProviderOrder.HEDGE, dry_run=dry_run)
