from decimal import Decimal

from ledger.models import Asset
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.precision import floor_precision
from market.models import PairSymbol


def reset_maker_amounts(value: int = 1000):
    for symbol in PairSymbol.objects.filter(asset__enable=True):
        price = get_external_price(symbol.asset.symbol, base_coin=Asset.USDT, side=BUY, allow_stale=True)

        symbol.maker_amount = floor_precision(
            (Decimal(value) / price), symbol.step_size)
        symbol.save()
