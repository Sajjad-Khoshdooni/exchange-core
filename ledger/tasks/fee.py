import math
from decimal import Decimal

from celery import shared_task

from ledger.models import NetworkAsset
from ledger.utils.price import get_trading_price_usdt, BUY
from provider.exchanges import BinanceSpotHandler


@shared_task(queue='celery')
def update_network_fees():
    network_assets = NetworkAsset.objects.all()

    for ns in network_assets:
        info = BinanceSpotHandler.get_network_info(ns.asset.symbol, ns.network.symbol)

        if info:
            symbol_pair = (ns.network.symbol, ns.asset.symbol)

            if symbol_pair not in [('TRX', 'USDT'), ('TRX', 'TRX'), ('BSC', 'USDT')]:
                info['withdrawFee'] = Decimal(info['withdrawFee']) * 2
                info['withdrawMin'] = Decimal(info['withdrawMin']) * 2

            withdraw_min = Decimal(info['withdrawMin'])
            if not withdraw_min:
                withdraw_min = Decimal(info['withdrawIntegerMultiple'])

            price = get_trading_price_usdt(ns.asset.symbol, BUY, raw_price=True)
            if price and withdraw_min:
                multiplier = max(math.ceil(5 / (price * withdraw_min)), 1)
            else:
                multiplier = 1

            info['withdrawMin'] = withdraw_min * multiplier  # to prevent prize withdrawing

            ns.withdraw_fee = info['withdrawFee']
            ns.withdraw_min = info['withdrawMin']
            ns.withdraw_max = info['withdrawMax']
            ns.binance_withdraw_enable = info['withdrawEnable']
        else:
            ns.binance_withdraw_enable = False

    NetworkAsset.objects.bulk_update(network_assets, fields=['withdraw_fee', 'withdraw_min', 'withdraw_max',
                                                             'binance_withdraw_enable'])
