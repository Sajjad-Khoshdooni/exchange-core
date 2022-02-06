import base64
import hmac
from _sha256 import sha256
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from yekta_config import secret

from provider.exchanges.base import BaseExchange
from provider.exchanges.binance_rules import futures_rules

binance_session = requests.Session()
binance_session.headers = {'X-MBX-APIKEY': secret('BINANCE_API_KEY', default='')}

BINANCE = 'binance'


class BinanceSpotHandler(BaseExchange):
    _base_api_url = 'https://api.binance.com'
    _session = binance_session

    exchange = BINANCE

    order_url = '/api/v3/order'

    @classmethod
    def collect_api(cls, endpoint, method='GET', **kwargs):
        data = kwargs.get('data', {})
        qp = data.pop('qp', True)

        data['timestamp'] = int(datetime.now().timestamp() * 1000)
        params = '&'.join(map(lambda i: f'{i[0]}={i[1]}', data.items()))
        sign = base64.b16encode(
            hmac.new(secret('BINANCE_SECRET_KEY', default='').encode(), params.encode(), sha256).digest()
        ).decode('latin-1').lower()
        data['signature'] = sign

        params += f'&signature={sign}'

        if method == 'GET':
            endpoint += '?' + params

        if method == 'GET':
            response = super().collect_api(endpoint, method=method)
        else:
            response = super().collect_api(endpoint, method=method, data=data)
        return response

    @classmethod
    def place_order(cls, symbol: str, side: str, amount: Decimal, order_type: str = BaseExchange.MARKET,
                         client_order_id: str = None) -> dict:

        side = side.upper()
        order_type = order_type.upper()

        assert side in (cls.SELL, cls.BUY)
        assert order_type in (cls.MARKET, cls.LIMIT)

        data = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': amount,
        }

        if client_order_id:
            data['newClientOrderId'] = client_order_id

        return cls.collect_api(cls.order_url, data=data, method=cls.POST)

    @classmethod
    def withdraw(cls, coin: str, network: str, address: str, amount: Decimal, address_tag: str = None,
                 client_id: str = None) -> dict:

        resp = cls.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data={
            'coin': coin,
            'network': network,
            'amount': amount,
            'address': address,
            'addressTag': address_tag,
            'withdrawOrderId': client_id
        })

        return resp

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/api/v3/account', method='GET') or {}


class BinanceFuturesHandler(BinanceSpotHandler):
    _base_api_url = 'https://fapi.binance.com'
    _testnet_api_url = 'https://testnet.binancefuture.com'

    order_url = '/fapi/v1/order'

    @classmethod
    def collect_api(cls, endpoint, method='POST', **kwargs):
        if method != 'GET':
            data = kwargs.get('data', {})
            data['qp'] = False
            kwargs['data'] = data

            headers = kwargs.get('headers', {}) or {}
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            kwargs['headers'] = headers

        data = kwargs.get('data', {})

        kwargs['data'] = data
        return super(BinanceFuturesHandler, cls).collect_api(endpoint, method, **kwargs)

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
