from decimal import Decimal

from celery import shared_task

from ledger.models import NetworkAsset
from provider.exchanges import BinanceSpotHandler


@shared_task(queue='celery')
def update_network_fees():
    network_assets = NetworkAsset.objects.all()

    for ns in network_assets:
        info = BinanceSpotHandler.get_network_info(ns.asset.symbol, ns.network.symbol)

        if info:
            if (ns.network.symbol, ns.asset.symbol) not in [('TRX', 'USDT'), ('TRX', 'TRX'), ('BSC', 'USDT')]:
                info['withdrawFee'] = Decimal(info['withdrawFee']) * 2
                info['withdrawMin'] = Decimal(info['withdrawMin']) * 2

            ns.withdraw_fee = info['withdrawFee']
            ns.withdraw_min = info['withdrawMin']
            ns.withdraw_max = info['withdrawMax']
            ns.binance_withdraw_enable = info['withdrawEnable']
        else:
            ns.binance_withdraw_enable = False

    NetworkAsset.objects.bulk_update(network_assets, fields=['withdraw_fee', 'withdraw_min', 'withdraw_max', 'binance_withdraw_enable'])