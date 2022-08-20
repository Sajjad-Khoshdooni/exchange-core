from ledger.models import Asset
from ledger.utils.overview import AssetOverview
from provider.models import ProviderOrder


def reset_assets_hedge(asset: Asset = None):
    overview = AssetOverview()

    assets = Asset.candid_objects.all().exclude(hedge_method=Asset.HEDGE_NONE)

    if asset:
        assets = assets.filter(id=asset.id)

    for asset in assets:
        calc_hedge = ProviderOrder.get_hedge(asset)
        hedge = overview.get_hedge_amount(asset)
        diff = hedge - calc_hedge

        if overview.get_price(asset.symbol) * abs(diff) > 1:
            ProviderOrder.objects.create(
                exchange='fake',
                asset=asset,
                amount=abs(diff),
                scope=ProviderOrder.FAKE,
                side=ProviderOrder.BUY if diff > 0 else ProviderOrder.SELL,
                hedge_amount=calc_hedge
            )

        ProviderOrder.try_hedge_for_new_order(asset, ProviderOrder.HEDGE)
