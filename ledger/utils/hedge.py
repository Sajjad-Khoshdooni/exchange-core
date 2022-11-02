from ledger.models import Asset
from ledger.utils.overview import AssetOverview
from ledger.utils.provider import get_provider_requester


def reset_assets_hedge(asset: Asset = None):
    overview = AssetOverview()

    assets = Asset.live_objects.filter(hedge=True)

    if asset:
        assets = assets.filter(id=asset.id)

    for asset in assets:
        calc_hedge = get_provider_requester().get_hedge_amount(asset)
        hedge = overview.get_hedge_amount(asset)
        diff = hedge - calc_hedge

        if overview.get_price(asset.symbol) * abs(diff) > 1:
            ProviderOrder.objects.create(
                exchange='fake',
                asset=asset,
                amount=abs(diff),
                scope='fake',
                side=ProviderOrder.BUY if diff > 0 else ProviderOrder.SELL,
                hedge_amount=calc_hedge
            )

        hedge_asset(asset)