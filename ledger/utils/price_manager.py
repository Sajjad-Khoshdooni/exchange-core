from datetime import datetime
from decimal import Decimal

from ledger.utils.cache import cache_for


@cache_for(time=20)
def prefetch_all_prices(side: str, allow_dust: bool=False):
    from ledger.utils.price import get_prices_dict
    from ledger.models import Asset

    coins = list(Asset.live_objects.values_list('symbol', flat=True))

    return get_prices_dict(
        coins=coins,
        side=side,
        allow_dust=allow_dust
    )


class PriceManager:
    _prices = None

    def __init__(self, fetch_all: bool = False, side: str = None, coins: list = None, allow_dust: bool = False):
        self._default_prices = {}

        if fetch_all or coins:
            from ledger.utils.price import get_prices_dict
            from ledger.models import Asset

            if fetch_all:
                self._default_prices = prefetch_all_prices(side, allow_dust=allow_dust)
            else:
                self._default_prices = get_prices_dict(
                    coins=coins,
                    side=side,
                    allow_dust=allow_dust
                )

    def __enter__(self):
        PriceManager._prices = {}

    def __exit__(self, exc_type, exc_val, exc_tb):
        PriceManager._prices = None

    @classmethod
    def active(cls):
        return cls._prices is not None

    @classmethod
    def get_price(cls, coin: str, side: str, exchange: str, market_symbol: str, now: datetime = None):
        return cls._prices.get((coin, side, exchange, market_symbol, now))

    @classmethod
    def set_price(cls, coin: str, side: str, exchange: str, market_symbol: str, now: datetime, price: Decimal):
        cls._prices[(coin, side, exchange, market_symbol, now)] = price
