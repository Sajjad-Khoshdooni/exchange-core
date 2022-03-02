from datetime import datetime
from decimal import Decimal


class PriceManager:
    _prices = None

    def __init__(self, fetch_all: bool = False, side: str = None, coins: list = None):
        self._default_prices = {}

        if fetch_all or coins:
            from ledger.utils.price import get_prices_dict
            from ledger.models import Asset

            if fetch_all:
                coins = list(Asset.live_objects.values_list('symbol', flat=True))

            self._default_prices = get_prices_dict(
                coins=coins,
                side=side
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
