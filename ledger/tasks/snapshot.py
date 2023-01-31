from celery import shared_task
from django.utils import timezone

from ledger.models import SystemSnapshot, Asset, AssetSnapshot
from ledger.utils.overview import AssetOverview
from ledger.utils.price import get_prices_dict, BUY


@shared_task(queue='history')
def create_snapshot():
    now = timezone.now()

    overview = AssetOverview(calculated_hedge=True)

    system_snapshot = SystemSnapshot(
        created=now,
        usdt_price=overview.usdt_irt,
        hedge=overview.get_total_hedge_value(),

        total=overview.get_all_real_assets_value(),
        users=overview.get_all_users_asset_value(),
        exchange=overview.get_exchange_assets_usdt(),
        exchange_potential=overview.get_exchange_potential_usdt(),
        reserved=overview.get_total_reserved_assets_value(),

        margin_insurance=overview.get_margin_insurance_balance(),
        prize=overview.get_all_prize_value(),
    )

    asset_snapshots = []

    assets = Asset.live_objects.all()

    prices = get_prices_dict(coins=list(assets.values_list('symbol', flat=True)), side=BUY, allow_stale=True)

    for asset in assets:
        asset_snapshots.append(
            AssetSnapshot(
                created=now,
                asset=asset,
                price=prices.get(asset.symbol, 0),
                hedge_amount=overview.get_hedge_amount(asset.symbol),
                hedge_value=overview.get_hedge_value(asset.symbol),
                calc_hedge_amount=overview.get_calculated_hedge(asset.symbol),

                total_amount=overview.get_real_assets(asset.symbol),
                users_amount=overview.get_users_asset_amount(asset.symbol),
            )
        )

    system_snapshot.save()
    AssetSnapshot.objects.bulk_create(asset_snapshots)
