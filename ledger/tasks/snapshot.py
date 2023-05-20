from celery import shared_task
from django.utils import timezone

from ledger.models import SystemSnapshot, Asset, AssetSnapshot
from ledger.utils.overview import AssetOverview
from ledger.utils.external_price import get_external_usdt_prices, BUY


@shared_task(queue='history')
def create_snapshot():
    now = timezone.now()

    overview = AssetOverview(calculated_hedge=True)

    system_snapshot = SystemSnapshot(
        created=now,
        usdt_price=overview.usdt_irt,
        hedge=overview.get_total_hedge_value(),
        cum_hedge=overview.get_total_cumulative_hedge_value(),

        total=overview.get_all_real_assets_value(),
        users=overview.get_all_users_asset_value(),
        exchange=overview.get_exchange_assets_usdt(),
        exchange_potential=overview.get_exchange_potential_usdt(),
        reserved=overview.get_total_reserved_assets_value(),

        margin_insurance=overview.get_margin_insurance_balance(),
        prize=overview.get_all_prize_value(),

        binance_margin_ratio=overview.get_binance_margin_ratio(),
    )

    assets = Asset.live_objects.all()

    prices = get_external_usdt_prices(
        coins=list(assets.values_list('symbol', flat=True)),
        side=BUY,
        allow_stale=True,
        set_bulk_cache=True
    )

    for asset in assets.filter(assetsnapshot__isnull=True):
        AssetSnapshot.objects.create(
            asset=asset,
            price=0,
            hedge_amount=0,
            hedge_value=0,
            hedge_value_abs=0,
            calc_hedge_amount=0,
            total_amount=0,
            users_amount=0,
        )

    asset_snapshots = list(AssetSnapshot.objects.filter(asset__enable=True))

    for s in asset_snapshots:
        asset = s.asset

        s.price = prices.get(asset.symbol, 0)
        s.hedge_amount = overview.get_hedge_amount(asset.symbol)
        s.hedge_value = overview.get_hedge_value(asset.symbol)
        s.hedge_value_abs = abs(s.hedge_value)
        s.calc_hedge_amount = overview.get_calculated_hedge(asset.symbol)
        s.total_amount = overview.get_real_assets(asset.symbol)
        s.users_amount = overview.get_users_asset_amount(asset.symbol)

    AssetSnapshot.objects.bulk_update(asset_snapshots, fields=[
        'price', 'hedge_amount', 'hedge_value', 'calc_hedge_amount', 'total_amount', 'users_amount'
    ])

    system_snapshot.save()
