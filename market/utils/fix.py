from ledger.models import Asset
from ledger.utils.precision import get_precision
from market.models import PairSymbol


def create_symbol_from_pair(asset: Asset, base_asset: Asset):
    symbol, created = PairSymbol.objects.get_or_create(
        asset=asset, base_asset=base_asset, defaults={
            'name': f'{asset.symbol}{base_asset.symbol}',
            'tick_size': asset.price_precision_irt if base_asset.symbol == 'IRT' else asset.price_precision_usdt,
            'step_size': get_precision(asset.trade_quantity_step),
            'min_trade_quantity': asset.min_trade_quantity,
            'max_trade_quantity': asset.max_trade_quantity,
            'maker_amount': min(10000 * asset.min_trade_quantity, asset.max_trade_quantity / 100)
        }
    )

    return symbol


def create_symbols_for_asset(asset: Asset):
    if asset.symbol == Asset.IRT:
        return

    irt_asset = Asset.objects.get(symbol=Asset.IRT)
    usdt_asset = Asset.objects.get(symbol=Asset.USDT)

    base_assets = [irt_asset, usdt_asset]

    if asset.symbol == Asset.USDT:
        base_assets = [irt_asset]

    for base_asset in base_assets:
        create_symbol_from_pair(asset, base_asset)


def create_missing_symbols():
    irt_asset = Asset.objects.get(symbol='IRT')
    usdt_asset = Asset.objects.get(symbol='USDT')

    for asset in Asset.objects.exclude(symbol='IRT'):
        for base_asset in (irt_asset, usdt_asset):
            if asset.symbol == 'USDT' and base_asset.symbol == 'USDT':
                continue

            create_symbol_from_pair(asset, base_asset)
