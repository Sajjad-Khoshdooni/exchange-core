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
        handler = ns.asset.get_hedger()
        info = handler. get_network_info(ns.asset.symbol, ns.network.symbol)

        if info:
            symbol_pair = (ns.network.symbol, ns.asset.symbol)
            withdraw_min = Decimal(info['withdrawMin'])
            withdraw_fee = Decimal(info['withdrawFee'])

            if symbol_pair not in [('TRX', 'USDT'), ('TRX', 'TRX'), ('BSC', 'USDT')]:
                withdraw_fee *= 2
                withdraw_min *= 2

            price = get_trading_price_usdt(ns.asset.symbol, BUY, raw_price=True)

            if price and withdraw_min:
                multiplier = max(math.ceil(5 / (price * withdraw_min)), 1)  # withdraw_min >= 5$
                withdraw_min *= multiplier

            if price and withdraw_fee:
                multiplier = max(math.ceil(Decimal('0.2') / (price * withdraw_fee)), 1)  # withdraw_fee >= 0.2$
                withdraw_fee *= multiplier

            ns.withdraw_fee = withdraw_fee
            ns.withdraw_min = withdraw_min
            ns.withdraw_max = info['withdrawMax']
            ns.hedger_withdraw_enable = info['withdrawEnable']
        else:
            ns.hedger_withdraw_enable = False

    NetworkAsset.objects.bulk_update(network_assets, fields=['withdraw_fee', 'withdraw_min', 'withdraw_max',
                                                             'hedger_withdraw_enable'])
