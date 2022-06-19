from datetime import datetime
from decimal import Decimal
from typing import Union

from django.conf import settings

from ledger.utils.cache import get_cache_func_key, cache
from ledger.utils.precision import decimal_to_str

from provider.exchanges.sdk.binance_sdk import binance_spot_send_signed_request, binance_futures_send_signed_request, \
    binance_futures_send_public_request, binance_spot_send_public_request

BINANCE = 'interface'

MARKET, LIMIT = 'MARKET', 'LIMIT'
SELL, BUY = 'SELL', 'BUY'
GET, POST = 'GET', 'POST'

HOUR = 3600


class ExchangeHandler:
    MARKET_TYPE = ''

    @classmethod
    def mapping_exchange(cls, hedge_method: str):
        from provider.exchanges.interface.kucoin_interface import KucoinSpotHandler, KucoinFuturesHandler
        from ledger.models.asset import Asset
        mapping = {
            Asset.HEDGE_BINANCE_SPOT: BinanceSpotHandler,
            Asset.HEDGE_BINANCE_FUTURE: BinanceFuturesHandler,
            Asset.HEDGE_KUCOIN_SPOT: KucoinSpotHandler,
            Asset.HEDGE_KUCOIN_FUTURE: KucoinFuturesHandler
        }
        if hedge_method:
            return mapping[hedge_method]()
        else:
            return mapping[Asset.HEDGE_BINANCE_FUTURE]()

    def get_trading_symbol(self, symbol: str) -> str:
        return NotImplementedError

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:
        return NotImplementedError

    def withdraw(self, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:
        return NotImplementedError

    def get_free_dict(self):
        return NotImplementedError

    def get_network_info(self, coin: str, network: str) -> Union[dict, None]:
        return NotImplementedError

    def get_withdraw_fee(self, coin: str, network: str) -> Decimal:
        return NotImplementedError

    def get_step_size(self, symbol: str) -> Decimal:
        return NotImplementedError

    def get_lot_min_quantity(self, symbol: str) -> Decimal:
        return NotImplementedError


class BinanceSpotHandler(ExchangeHandler):
    order_url = '/api/v3/order'
    MARKET_TYPE = 'spot'

    @classmethod
    def collect_api(cls, url: str, method: str = 'POST', data: dict = None, signed: bool = True,
                    cache_timeout: int = None):
        cache_key = None

        if cache_timeout:
            cache_key = get_cache_func_key(cls, url, method, data, signed)
            result = cache.get(cache_key)

            if result is not None:
                return result

        result = cls._collect_api(url=url, method=method, data=data, signed=signed)

        if cache_timeout:
            cache.set(cache_key, result, cache_timeout)

        return result

    @classmethod
    def _collect_api(cls, url: str, method: str = 'GET', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING:
            return {}

        data = data or {}

        if signed:
            return binance_spot_send_signed_request(method, url, data)
        else:
            return binance_spot_send_public_request(url, data)

    def get_trading_symbol(self, coin: str) -> str:
        if coin == 'LUNC':
            base = 'BUSD'
        else:
            base = 'USDT'

        if coin == 'BTT':
            coin = 'BTTC'

        return coin + base

    def place_order(self, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
                    client_order_id: str = None) -> dict:

        side = side.upper()
        order_type = order_type.upper()

        assert side in (SELL, BUY)
        assert order_type in (MARKET, LIMIT)

        data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': decimal_to_str(amount),
        }

        if client_order_id:
            data['newClientOrderId'] = client_order_id

        return self.collect_api(self.order_url, data=data, method=POST)

    def withdraw(self, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:

        return self.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data={
            'coin': coin,
            'network': network,
            'amount': decimal_to_str(amount),
            'address': address,
            'addressTag': address_tag,
            'withdrawOrderId': client_id
        })

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/api/v3/account', method='GET') or {}

    def get_free_dict(self):
        balances_list = self.get_account_details()['balances']
        return {b['asset']: Decimal(b['free']) for b in balances_list}

    @classmethod
    def get_all_coins(cls):
        return cls.collect_api('/sapi/v1/capital/config/getall', method='GET', cache_timeout=HOUR)

    @classmethod
    def get_coin_data(cls, coin: str) -> Union[dict, None]:
        info = list(filter(lambda d: d['coin'] == coin, cls.get_all_coins()))

        if not info:
            return

        return info[0]

    def get_network_info(self, coin: str, network: str) -> Union[dict, None]:
        coin = self.get_coin_data(coin)
        if not coin:
            return

        networks = list(filter(lambda d: d['network'] == network, coin['networkList']))

        if networks:
            return networks[0]

    def get_withdraw_fee(self, coin: str, network: str) -> Decimal:
        info = self.get_network_info(coin, network)
        return Decimal(info['withdrawFee'])

    @classmethod
    def transfer(cls, asset: str, amount: float, market: str, transfer_type: int):
        return cls.collect_api(f'/sapi/v1/{market}/transfer', method='POST', data={
            'asset': asset, 'amount': amount, 'type': transfer_type
        })

    @classmethod
    def get_symbol_data(cls, symbol: str) -> Union[dict, None]:
        data = cls.collect_api('/api/v3/exchangeInfo', data={'symbol': symbol}, signed=False, cache_timeout=HOUR)

        if not data:
            return

        return data['symbols'][0]

    @classmethod
    def get_lot_size_data(cls, symbol: str) -> Union[dict, None]:
        data = cls.get_symbol_data(symbol)

        if not data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['filters']))
        return filters and filters[0]

    def get_step_size(self, symbol: str) -> Decimal:
        lot_size = self.get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['stepSize'])

    def get_lot_min_quantity(self, symbol: str) -> Decimal:
        lot_size = self.get_lot_size_data(symbol)
        return lot_size and Decimal(lot_size['minQty'])


class BinanceFuturesHandler(BinanceSpotHandler):
    order_url = '/fapi/v1/order'
    MARKET = 'fut'
    renamed_symbols = {
        'SHIBUSDT': '1000SHIBUSDT'
    }

    @classmethod
    def _collect_api(cls, url: str, method: str = 'POST', data: dict = None, signed: bool = True):
        if settings.DEBUG_OR_TESTING:
            return {}

        data = data or {}

        if signed:
            return binance_futures_send_signed_request(method, url, data)
        else:
            return binance_futures_send_public_request(url, data)

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/fapi/v2/account', method='GET')

    @classmethod
    def get_order_detail(cls, symbol: str, order_id: str):
        return cls.collect_api(
            '/fapi/v1/order', method='GET', data={'orderId': order_id, 'symbol': symbol}
        )

    @classmethod
    def get_symbol_data(cls, symbol: str) -> Union[dict, None]:
        if symbol in cls.renamed_symbols:
            symbol = cls.renamed_symbols[symbol]

        data = cls.collect_api('/fapi/v1/exchangeInfo', signed=False, cache_timeout=HOUR)

        if not data:
            return

        data = data['symbols']
        coin_data = list(filter(lambda f: f['symbol'] == symbol, data))

        if not coin_data:
            return

        return coin_data[0]

    @classmethod
    def get_lot_size_data(cls, symbol: str) -> Union[dict, None]:
        coin_data = cls.get_symbol_data(symbol)
        if not coin_data:
            return

        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', coin_data['filters']))

        if filters:
            lot_size = filters[0]

            if symbol in cls.renamed_symbols:
                lot_size['stepSize'] = Decimal(lot_size['stepSize']) * 1000
                lot_size['minQty'] = Decimal(lot_size['minQty']) * 1000

            return lot_size

    @classmethod
    def get_incomes(cls, start_date: datetime, end_date: datetime) -> list:
        return cls.collect_api(
            '/fapi/v1/income', method='GET', data={
                # 'incomeType': income_type,
                'startTime': int(start_date.timestamp() * 1000),
                'endTime': int(end_date.timestamp() * 1000),
                'limit': 1000
            }
        )
