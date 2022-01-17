import base64
import hmac
from _sha256 import sha256
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from yekta_config import secret

from provider.exchanges.base import BaseExchange

binance_session = requests.Session()
binance_session.headers = {'X-MBX-APIKEY': secret('BINANCE_API_KEY', default='')}

BINANCE = 'binance'


class BinanceHandler(BaseExchange):
    _base_api_url = 'https://api.binance.com'
    _session = binance_session

    exchange = BINANCE

    @classmethod
    def collect_api(cls, endpoint, method='GET', **kwargs):
        if settings.DEBUG:
            print('requesting ', kwargs)
            return {'orderId': 1}

        data = kwargs.get('data', {})
        qp = data.pop('qp', True)

        data['timestamp'] = int(datetime.now().timestamp() * 1000)
        params = '&'.join(map(lambda i: f'{i[0]}={i[1]}', data.items()))
        sign = base64.b16encode(
            hmac.new(secret('BINANCE_SECRET_KEY', default='').encode(), params.encode(), sha256).digest()
        ).decode('latin-1').lower()
        params += f'&signature={sign}'

        if method == 'GET':
            endpoint += '?' + params

        if method == 'GET':
            response = super().collect_api(endpoint, method=method)
        else:
            response = super().collect_api(endpoint, method=method, data=params)
        return response

    @classmethod
    def spot_place_order(cls, symbol: str, side: str, amount: Decimal, order_type: str = BaseExchange.MARKET,
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

        return cls.collect_api('/api/v3/order', data=data, method=cls.POST)

