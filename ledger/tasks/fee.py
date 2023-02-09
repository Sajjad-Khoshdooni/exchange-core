import logging

from celery import shared_task

from ledger.models import NetworkAsset
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger()


@shared_task(queue='celery')
def update_network_fees():
    network_assets = NetworkAsset.objects.all().exclude(can_withdraw=False, can_deposit=False)

    for ns in network_assets:
        info = get_provider_requester().get_network_info(ns.asset.symbol, ns.network.symbol)
        if not info:
            logger.info('Ignoring network asset update for (%s, %s) because of no data provided' % (ns.asset, ns.network))
            continue

        info = info[0]

        ns.update_with_provider(info)
