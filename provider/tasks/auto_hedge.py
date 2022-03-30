from celery import shared_task

from ledger.models import Asset
from provider.models import ProviderOrder


@shared_task(queue='binance')
def auto_hedge_assets():
    for asset in Asset.objects.all():
        ProviderOrder.try_hedge_for_new_order(asset, ProviderOrder.HEDGE)

