import math

from ledger.models import Asset
from ledger.utils.external_price import BUY, get_external_price
from market.consts import OTC_MIN_HARD_FIAT_VALUE
from market.models import PairSymbol


def create_symbols_for_asset(asset: Asset):
    if asset.symbol == Asset.IRT:
        return

    irt_asset = Asset.objects.get(symbol=Asset.IRT)
    usdt_asset = Asset.objects.get(symbol=Asset.USDT)

    base_assets = [irt_asset, usdt_asset]

    if asset.symbol == Asset.USDT:
        base_assets = [irt_asset]

    price_irt = get_external_price(
        coin=asset.symbol,
        base_coin=Asset.IRT,
        side=BUY,
    )

    step_size = math.ceil(math.log10(price_irt / OTC_MIN_HARD_FIAT_VALUE))

    for base_asset in base_assets:
        price_usdt = get_external_price(
            coin=asset.symbol,
            base_coin=Asset.USDT,
            side=BUY,
            allow_stale=True,
        )

        PairSymbol.objects.get_or_create(
            asset=asset, base_asset=base_asset, defaults={
                'name': f'{asset.symbol}{base_asset.symbol}',
                'tick_size': asset.price_precision_irt if base_asset.symbol == 'IRT' else asset.price_precision_usdt,
                'step_size': step_size,
                'min_trade_quantity': 1,
                'max_trade_quantity': 1e8,
            }
        )


def check_pair_symbol(p, up: bool = False):
    asset = p.asset
    price_irt = get_external_price(
        coin=asset.symbol,
        base_coin=Asset.IRT,
        side=BUY,
    )
    if not price_irt:
        print('ignore %s due to null price' % p)
        return
    step_size = math.ceil(math.log10(price_irt / OTC_MIN_HARD_FIAT_VALUE))
    if step_size > p.step_size:
        print(p, step_size, p.step_size, step_size > p.step_size)
        if up:
            p.step_size = step_size
            p.save(update_fields=['step_size'])
