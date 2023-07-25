from celery.app import shared_task
from django.utils import timezone

from accounting.utils.vault import update_provider_vaults, update_hot_wallet_vault, update_gateway_vaults, \
    update_asset_prices, update_cold_wallet_vaults, update_reserved_assets_value, update_bank_vaults
from ledger.models import Asset
from ledger.tasks import create_snapshot
from ledger.utils.external_price import SELL, get_external_price, get_external_usdt_prices


@shared_task(queue='vault')
def update_vaults():
    assets = Asset.live_objects.all()

    irt_usdt = get_external_price(
        coin=Asset.IRT,
        base_coin=Asset.USDT,
        side=SELL,
        allow_stale=True
    )

    prices = get_external_usdt_prices(
        coins=list(assets.values_list('symbol', flat=True)),
        side=SELL,
        allow_stale=True,
        set_bulk_cache=True
    )
    prices['IRT'] = irt_usdt

    now = timezone.now()

    update_provider_vaults(now, prices)
    update_hot_wallet_vault(now, prices)
    update_gateway_vaults(now, prices)
    update_bank_vaults(now, prices)
    update_cold_wallet_vaults(now, prices)

    update_reserved_assets_value(now, prices)
    update_asset_prices(now, prices)
    create_snapshot(now, prices)
