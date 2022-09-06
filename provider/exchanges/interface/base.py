from decimal import Decimal
from typing import Union

from ledger.utils.cache import get_cache_func_key, cache


MARKET, LIMIT = 'MARKET', 'LIMIT'
SELL, BUY = 'SELL', 'BUY'
GET, POST = 'GET', 'POST'

HOUR = 3600


class ExchangeHandler:
    MARKET_TYPE = ''
    NAME = ''

    SYMBOL_MAPPING = {
        'ELON': '1000ELON',
        'BABYDOGE': '1M-BABYDOGE',
        'FLOKI': '1000FLOKI',
        'QUACK': '1M-QUACK',
        'STARL': '1000STARL',
        'SAFEMARS': '1M-SAFEMARS',
        'R': 'REV',
    }

    COIN_COEFFICIENTS = {
        'ELON': Decimal('1000'),
        'BABYDOGE': Decimal('1000000'),
        'FLOKI': Decimal('1000'),
        'QUACK': Decimal('1000000'),
        'STARL': Decimal('1000'),
        'SAFEMARS': Decimal('1000000'),
    }

    @classmethod
    def get_handler(cls, name: str):
        from provider.exchanges import BinanceSpotHandler, BinanceFuturesHandler, KucoinSpotHandler, KucoinFuturesHandler, MexcFuturesHandler, MexcSpotHandler
        from ledger.models.asset import Asset

        mapping = {
            Asset.HEDGE_BINANCE_SPOT: BinanceSpotHandler,
            Asset.HEDGE_BINANCE_FUTURE: BinanceFuturesHandler,
            Asset.HEDGE_KUCOIN_SPOT: KucoinSpotHandler,
            Asset.HEDGE_KUCOIN_FUTURE: KucoinFuturesHandler,
            Asset.HEDGE_MEXC_SPOT: MexcSpotHandler,
            Asset.HEDGE_MEXC_FUTURES: MexcFuturesHandler,
        }

        return mapping.get(name, BinanceSpotHandler)()

    @classmethod
    def rename_original_coin_to_internal(cls, coin: str):
        return cls.SYMBOL_MAPPING.get(coin, coin)

    @classmethod
    def rename_internal_coin_to_original(cls, coin: str):
        reversed_mapping = {v: k for (k, v) in cls.SYMBOL_MAPPING.items()}
        return reversed_mapping.get(coin, coin)

    @classmethod
    def get_coin_coefficient(cls, coin: str):
        coin = cls.rename_internal_coin_to_original(coin)
        return cls.COIN_COEFFICIENTS.get(coin, 1)

    def collect_api(self, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):
        cache_key = None
        # if cache_timeout:
        #     cache_key = get_cache_func_key(self.__class__, url, method, data, signed)
        #     result = cache.get(cache_key)
        #     if result is not None:
        #         return result

        result = self._collect_api(url=url, method=method, data=data, signed=signed)

        if cache_timeout:
            cache.set(cache_key, result, cache_timeout)

        return result

    def get_min_notional(self):
        return 10

    def _collect_api(self, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        raise NotImplementedError

    def get_trading_symbol(self, symbol: str) -> str:
        raise NotImplementedError

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:
        raise NotImplementedError

    def withdraw(self, coin: str, network, address: str, transfer_amount: Decimal,
                 fee_amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:
        raise NotImplementedError

    def get_account_details(self):
        raise NotImplementedError

    def get_free_dict(self):
        raise NotImplementedError

    def get_all_coins(self):
        raise NotImplementedError

    def get_coin_data(self, coin: str) -> Union[dict, None]:
        raise NotImplementedError

    def get_network_info(self, coin: str, network) -> Union[dict, None]:
        raise NotImplementedError

    def get_withdraw_fee(self, coin: str, network) -> Decimal:
        raise NotImplementedError

    def transfer(self, asset: str, amount: float, market: str, transfer_type: int):
        raise NotImplementedError

    def get_symbol_data(self, symbol: str) -> Union[dict, None]:
        raise NotImplementedError

    def get_step_size(self, symbol: str) -> Decimal:
        raise NotImplementedError

    def get_lot_min_quantity(self, symbol: str) -> Decimal:
        raise NotImplementedError

    def get_withdraw_status(self, withdraw_id: str) -> dict:
        raise NotImplementedError

    def get_spot_handler(self) -> 'ExchangeHandler':
        raise NotImplementedError

