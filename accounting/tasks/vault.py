from celery.app import shared_task
from django.utils import timezone

from accounting.utils.vault import update_provider_vaults, update_hot_wallet_vault, update_gateway_vaults, \
    update_asset_prices, update_cold_wallet_vaults, update_reserved_assets_value
from ledger.models import Asset
from ledger.utils.external_price import SELL, get_external_price


@shared_task(queue='vault')
def update_vaults():
    usdt_irt = get_external_price(
        coin=Asset.USDT,
        base_coin=Asset.IRT,
        side=SELL,
        allow_stale=True
    )
    now = timezone.now()

    update_provider_vaults(now, usdt_irt)
    update_hot_wallet_vault(now, usdt_irt)
    update_gateway_vaults(now, usdt_irt)
    update_cold_wallet_vaults(usdt_irt)
    update_reserved_assets_value(usdt_irt)

    update_asset_prices()
