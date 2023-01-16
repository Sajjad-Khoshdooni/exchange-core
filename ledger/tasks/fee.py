import logging
import math
from decimal import Decimal

from celery import shared_task

from ledger.models import NetworkAsset
from ledger.utils.price import get_trading_price_usdt, BUY
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger()


@shared_task(queue='celery')
def update_network_fees():
    network_assets = NetworkAsset.objects.all().exclude(can_withdraw=False, can_deposit=False)

    for ns in network_assets:
        info = get_provider_requester().get_network_info(ns.asset, ns.network)
        if not info:
            logger.info('Ignoring network asset update for (%s, %s) because of no data provided' % (ns.asset, ns.network))
            continue

        symbol_pair = (ns.network.symbol, ns.asset.symbol)
        withdraw_fee = info.withdraw_fee
        withdraw_min = info.withdraw_min

        if symbol_pair in [('TRX', 'USDT'), ('BSC', 'USDT'), ('BNB', 'USDT'), ('SOL', 'USDT')]:
            withdraw_fee = Decimal('0.8')
            withdraw_min = Decimal(10)
        elif symbol_pair not in [('TRX', 'USDT'), ('TRX', 'TRX'), ('BSC', 'USDT'), ('BNB', 'USDT'), ('SOL', 'USDT')]:
            withdraw_fee *= 2
            withdraw_min = max(withdraw_min, 2 * withdraw_fee)

        price = get_trading_price_usdt(ns.asset.symbol, BUY, raw_price=True)

        if price and withdraw_min:
            multiplier = max(math.ceil(5 / (price * withdraw_min)), 1)  # withdraw_min >= 5$
            withdraw_min *= multiplier

        if price and withdraw_fee:
            multiplier = max(math.ceil(Decimal('0.2') / (price * withdraw_fee)), 1)  # withdraw_fee >= 0.2$
            withdraw_fee *= multiplier

        withdraw_min = max(
            withdraw_min,
            info.withdraw_min + withdraw_fee - info.withdraw_fee
        )

        ns.withdraw_fee = withdraw_fee
        ns.withdraw_min = withdraw_min
        ns.withdraw_max = info.withdraw_max
        ns.hedger_withdraw_enable = info.withdraw_enable
        ns.hedger_deposit_enable = info.deposit_enable

    NetworkAsset.objects.bulk_update(network_assets, fields=[
        'withdraw_fee', 'withdraw_min', 'withdraw_max', 'hedger_withdraw_enable', 'hedger_deposit_enable'
    ])
