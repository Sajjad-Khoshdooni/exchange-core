from datetime import datetime
from decimal import Decimal

from django.conf import settings

from ledger.utils.cache import cache_for
from ledger.utils.precision import decimal_to_str
from provider.exchanges.binance.sdk import spot_send_signed_request, futures_send_signed_request
from provider.exchanges.binance_rules import futures_rules

BINANCE = 'binance'

MARKET, LIMIT = 'MARKET', 'LIMIT'
SELL, BUY = 'SELL', 'BUY'
GET, POST = 'GET', 'POST'


class BinanceSpotHandler:
    order_url = '/api/v3/order'

    @classmethod
    def collect_api(cls, url: str, method: str = 'GET', data: dict = None):
        if settings.DEBUG:
            return {}

        return spot_send_signed_request(method, url, data or {})

    @classmethod
    def place_order(cls, symbol: str, side: str, amount: Decimal, order_type: str = MARKET,
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

        return cls.collect_api(cls.order_url, data=data, method=POST)

    @classmethod
    def withdraw(cls, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:

        return cls.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data={
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

    @classmethod
    def get_free_dict(cls):
        balances_list = BinanceSpotHandler.get_account_details()['balances']
        return {b['asset']: Decimal(b['free']) for b in balances_list}

    @classmethod
    @cache_for(time=120)
    def get_all_coins(cls):
        return cls.collect_api('/sapi/v1/capital/config/getall', method='GET')

    @classmethod
    def get_network_info(cls, coin: str, network: str) -> dict:
        info = list(filter(lambda d: d['coin'] == coin, cls.get_all_coins()))

        if not info:
            return

        coin = info[0]
        networks = list(filter(lambda d: d['network'] == network, coin['networkList']))

        if networks:
            return networks[0]

    @classmethod
    def get_withdraw_fee(cls, coin: str, network: str) -> Decimal:
        info = cls.get_network_info(coin, network)
        return Decimal(info['withdrawFee'])

    @classmethod
    def transfer(cls, asset: str, amount: float, market: str, transfer_type: int):
        return cls.collect_api(f'/sapi/v1/{market}/transfer', method='POST', data={
            'asset': asset, 'amount': amount, 'type': transfer_type
        })

    @classmethod
    def get_step_size(cls, symbol: str) -> Decimal:
        data = cls.collect_api('/api/v3/exchangeInfo', data={'symbol': symbol + 'USDT'})
        filters = list(filter(lambda f: f['filterType'] == 'LOT_SIZE', data['symbols'][0]['filters']))
        lot_size = filters[0]

        return Decimal(lot_size['stepSize'])


class BinanceFuturesHandler(BinanceSpotHandler):
    order_url = '/fapi/v1/order'

    @classmethod
    def collect_api(cls, url: str, method: str = 'POST', data: dict = None):
        if settings.DEBUG:
            return {}

        return futures_send_signed_request(method, url, data or {})

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/fapi/v2/account', method='GET')

    @classmethod
    def get_order_detail(cls, symbol: str, order_id: str):
        return cls.collect_api(
            '/fapi/v1/order', method='GET', data={'orderId': order_id, 'symbol': symbol}
        )

    @classmethod
    def get_step_size(cls, symbol: str):
        return float(futures_rules.get(
            symbol, {'filters': {'LOT_SIZE': {'stepSize': 0.0001}}}
        )['filters']['LOT_SIZE']['stepSize'])

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
