from celery import shared_task

from ledger.models import NetworkAsset
from provider.exchanges import BinanceSpotHandler


@shared_task()
def update_network_fees():
    network_assets = NetworkAsset.objects.all()

    for ns in network_assets:
        info = BinanceSpotHandler.get_network_info(ns.asset.symbol, ns.network.symbol)

        if info:
            ns.withdraw_fee = info['withdrawFee']
            ns.withdraw_min = info['withdrawMin']
            ns.withdraw_max = info['withdrawMax']

    NetworkAsset.objects.bulk_update(network_assets, fields=['withdraw_fee', 'withdraw_min', 'withdraw_max'])