from decimal import Decimal

from ledger.utils.precision import floor_precision
from ledger.utils.price import get_trading_price_usdt, BUY
from market.models import PairSymbol


def reset_maker_amounts(value: int = 1000):
    for symbol in PairSymbol.objects.filter(asset__enable=True):
        symbol.maker_amount = floor_precision(
            (Decimal(value) / get_trading_price_usdt(symbol.asset.symbol, BUY, raw_price=True)), symbol.step_size)
        symbol.save()
