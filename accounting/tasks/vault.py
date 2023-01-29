from celery.app import shared_task
from django.utils import timezone

from accounting.utils.vault import update_provider_vaults, update_hot_wallet_vault, update_gateway_vaults, \
    update_asset_prices, update_cold_wallet_vaults
from ledger.utils.price import get_tether_irt_price, SELL


@shared_task(queue='vault')
def update_vaults():
    usdt_irt = get_tether_irt_price(SELL)
    now = timezone.now()

    update_provider_vaults(now, usdt_irt)
    update_hot_wallet_vault(now, usdt_irt)
    update_gateway_vaults(now, usdt_irt)
    update_cold_wallet_vaults(now, usdt_irt)

    update_asset_prices()
