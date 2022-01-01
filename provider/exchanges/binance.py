import base64
import hmac
from _sha256 import sha256
from datetime import datetime

import requests
from django.conf import settings
from yekta_config import secret

from provider.exchanges import BaseExchangeHandler

binance_session = requests.Session()
binance_session.headers = {'X-MBX-APIKEY': secret('binance-api-key', default='')}

BINANCE = 'binance'


class BinanceHandler(BaseExchangeHandler):
    _base_api_url = 'https://api.binance.com'
    _session = binance_session

    exchange = BINANCE

    @classmethod
    def collect_api(cls, endpoint, method='POST', **kwargs):
        if settings.DEBUG:
            return

        data = kwargs.get('data', {})
        qp = data.pop('qp', True)

        data['timestamp'] = int(datetime.now().timestamp() * 1000)
        params = '&'.join(map(lambda i: f'{i[0]}={i[1]}', data.items()))
        sign = base64.b16encode(
            hmac.new(secret('binance-secret-key', default='').encode(), params.encode(), sha256).digest()
        ).decode('latin-1').lower()
        params += f'&signature={sign}'

        if qp:
            url = f'{endpoint}?{params}'
        else:
            url = endpoint

        if method == 'GET':
            response = super(BinanceHandler, cls).collect_api(url, method=method)
        else:
            response = super(BinanceHandler, cls).collect_api(url, method=method, data=params)
        return response

    @classmethod
    def place_order(cls, symbol, order_type, amount, market='margin', client_order_id: str = None, **kwargs):
        amount = get_amount_floor_precision(symbol, BINANCE, amount)

        if market == 'spot':
            path = '/api/v3/order'
        else:
            path = '/sapi/v1/margin/order'

        data = {
            'symbol': symbol,
            'side': order_type.upper(),
            'type': kwargs.get('fill_type', MARKET).upper(),
            'quantity': amount,
            'newOrderRespType': kwargs.get('response_type', 'RESULT'),
            'qp': market == 'margin'
        }

        if client_order_id:
            data['newClientOrderId'] = client_order_id

        return cls.collect_api(path, data=data) or {}

    @classmethod
    def borrow(cls, asset, quantity, **kwargs):
        return cls.collect_api('/sapi/v1/margin/loan', method='POST', data={
            'asset': asset,
            'amount': quantity,
        })

    @classmethod
    def repay(cls, asset, quantity, **kwargs):
        resp = cls.collect_api('/sapi/v1/margin/repay', method='POST', data={
            'asset': asset,
            'amount': quantity,
        })
        if type(resp) == tuple and not resp[1]:
            free = float((list(filter(
                lambda a: a['asset'] == asset,
                cls.get_account_details().get('userAssets', [])
            )) or [{'free': 0}])[0]['free'])
            if not free:
                return resp

            return cls.collect_api('/sapi/v1/margin/repay', method='POST', data={
                'asset': asset,
                'amount': free,
            })

        return resp

    @classmethod
    def get_account_details(cls):
        return cls.collect_api('/sapi/v1/margin/account', method='GET') or {}

    @classmethod
    def get_account_spot_details(cls):
        return cls.collect_api('/api/v3/account', method='GET') or {}

    @classmethod
    def get_transfer_history(cls):
        return cls.collect_api('/sapi/v1/margin/transfer', method='GET') or {}

    @classmethod
    def withdraw(cls, coin_symbol: str, network: str, address: str, amount: float, address_tag: str = None,
                 client_withdraw_id: str = None) -> str:

        resp = cls.collect_api('/sapi/v1/capital/withdraw/apply', method='POST', data={
            'coin': coin_symbol,
            'network': network,
            'amount': amount,
            'address': address,
            'addressTag': address_tag,
            'withdrawOrderId': client_withdraw_id
        })

        return resp and resp['id']

    @classmethod
    def custom_operation(cls, api_path, method='POST', **kwargs):
        return cls.collect_api(api_path, method=method, data={**kwargs})

    @classmethod
    def get_coin_info(cls):
        return cls.collect_api('/sapi/v1/capital/config/getall', method='GET') or {}

    @classmethod
    def get_transfer_info(cls, coin_symbol: str, network: str) -> dict:
        info_list = list(filter(lambda info: info['coin'] == coin_symbol, cls.get_coin_info()))

        if not info_list:
            return

        info = info_list[0]

        network_info_list = list(filter(lambda net: net['network'] == network, info['networkList']))

        if not network_info_list:
            return

        return network_info_list[0]

    @classmethod
    def get_order_detail(cls, symbol, order_id):
        return cls.collect_api(
            '/sapi/v1/margin/order', method='GET', data={'orderId': order_id, 'symbol': symbol}
        ) or {'executedQty': 0, 'cummulativeQuoteQty': 0}
