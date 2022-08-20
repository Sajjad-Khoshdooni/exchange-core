from celery import shared_task
from django.utils import timezone

from ledger.models import SystemSnapshot, Asset, AssetSnapshot
from ledger.utils.overview import AssetOverview
from provider.models import ProviderOrder


@shared_task(queue='history')
def create_snapshot():
    now = timezone.now()

    overview = AssetOverview()

    system_snapshot = SystemSnapshot(
        created=now,
        usdt_price=overview.usdt_irt,
        hedge=overview.get_total_hedge_value(),
        cumulated_hedge=overview.get_cumulated_hedge_value(),

        total=overview.get_all_assets_usdt(),
        users=overview.get_all_users_asset_value(),
        exchange=overview.get_exchange_assets_usdt(),
        exchange_potential=overview.get_exchange_potential_usdt(),

        binance_futures=overview.total_margin_balance,
        binance_spot=overview.get_binance_spot_total_value(),
        internal=overview.get_internal_usdt_value(),
        fiat_gateway=overview.get_gateway_usdt(),
        investment=overview.get_total_investment(),
        cash=overview.get_total_cash(),
        margin_insurance=overview.get_margin_insurance_balance(),

        binance_futures_initial_margin=overview.total_initial_margin,
        binance_futures_maintenance_margin=overview.total_maintenance_margin,
        binance_futures_margin_balance=overview.total_margin_balance,
        binance_futures_available_balance=overview.get_futures_available_usdt(),
        binance_futures_margin_ratio=overview.margin_ratio,

        prize=overview.get_all_prize_value(),
    )

    asset_snapshots = []

    for asset in Asset.candid_objects.all():
        asset_snapshots.append(
            AssetSnapshot(
                created=now,
                asset=asset,
                price=overview.prices.get(asset.symbol, 0),
                hedge_amount=overview.get_hedge_amount(asset),
                hedge_value=overview.get_hedge_value(asset),
                calc_hedge_amount=ProviderOrder.get_hedge(asset),

                total_amount=overview.get_total_assets(asset),
                users_amount=overview.get_users_asset_amount(asset),

                provider_amount=overview.get_binance_balance(asset),
                internal_amount=overview.get_internal_deposits_balance(asset),
                investment_amount=overview.get_hedged_investment_amount(asset),
                cash_amount=overview.get_hedged_cash_amount(asset),
            )
        )

    system_snapshot.save()
    AssetSnapshot.objects.bulk_create(asset_snapshots)
