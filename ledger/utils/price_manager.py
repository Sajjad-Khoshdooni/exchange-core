import logging

from ledger.utils.cache import cache_for

logger = logging.getLogger(__name__)


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
    _fetch_all = None
    _tether_prices = None

    def __init__(self, fetch_all: bool = False, side: str = None, coins: list = None, allow_stale: bool = True):
        self.fetch_all = fetch_all
        self.side = side
        self.coins = coins
        self.allow_stale = allow_stale
        self.parent_price_manager = True

    def __enter__(self):
        if PriceManager._prices is not None:
            self.parent_price_manager = False
            if PriceManager._fetch_all:
                return
        PriceManager._prices = {}
        PriceManager._tether_prices = {}
        PriceManager._fetch_all = self.fetch_all

        if self.side:
            sides = [self.side]
        else:
            sides = ['buy', 'sell']

        self._prices = {}
        from ledger.utils.price import get_prices_dict, get_tether_irt_price

        for side in sides:
            if self.fetch_all:
                prices = prefetch_all_prices(side, allow_stale=self.allow_stale)
            else:
                prices = get_prices_dict(
                    coins=self.coins,
                    side=side,
                    allow_stale=self.allow_stale
                )

            for c, price in prices.items():
                PriceManager._prices[c, side] = price

            PriceManager._tether_prices[side] = get_tether_irt_price(side, allow_stale=self.allow_stale)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.parent_price_manager:
            PriceManager._prices = None
            PriceManager._tether_prices = None
            PriceManager._fetch_all = None

    @classmethod
    def active(cls):
        return cls._prices is not None

    @classmethod
    def get_price(cls, coin: str, side: str):
        return cls._prices.get((coin, side))

    @classmethod
    def get_tether_price(cls, side: str):
        return cls._tether_prices.get(side)
