from datetime import datetime
from decimal import Decimal


class PriceManager:
    _prices = None

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
