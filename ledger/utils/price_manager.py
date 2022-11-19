from datetime import datetime
from decimal import Decimal

from ledger.utils.cache import cache_for


@cache_for(time=20)
def prefetch_all_prices(side: str, allow_stale: bool = False):
    from ledger.utils.price import get_prices_dict
    from ledger.models import Asset

    coins = list(Asset.live_objects.values_list('symbol', flat=True))

    return get_prices_dict(
        coins=coins,
        side=side,
        allow_stale=allow_stale
    )


class PriceManager:
    _prices = None

    def __init__(self, fetch_all: bool = False, side: str = None, coins: list = None, allow_stale: bool = True):

        if side:
            sides = [side]
        else:
            sides = ['buy', 'sell']

        self._prices = {}
        from ledger.utils.price import get_prices_dict

        for side in sides:
            if fetch_all:
                prices = prefetch_all_prices(side, allow_stale=allow_stale)
            else:
                prices = get_prices_dict(
                    coins=coins,
                    side=side,
                    allow_stale=allow_stale
                )

            for c, price in prices.items():
                self._prices[c, side] = price

    def __enter__(self):
        PriceManager._prices = {}

    def __exit__(self, exc_type, exc_val, exc_tb):
        PriceManager._prices = None

    @classmethod
    def active(cls):
        return cls._prices is not None

    @classmethod
    def get_price(cls, coin: str, side: str):
        return cls._prices.get((coin, side))
