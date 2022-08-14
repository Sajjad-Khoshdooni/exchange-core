import base64
import hashlib
import hmac

import requests
from django.conf import settings
from rest_framework.utils import json
from yekta_config import secret
from yekta_config.config import config

from provider.exchanges.sdk.binance_sdk import get_timestamp

if not settings.DEBUG:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = "https://api-futures.kucoin.com"
else:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = "https://api-futures.kucoin.com"


def kucoin_spot_send_public_request(endpoint, method='POST', **kwargs):
    pass


def add_sign_kucoin_spot(params_str, timestamp, http_method):
    headers = {}
    _secret_key = secret('KC-SECRET-KEY')
    _secret_passphrase = secret('KC-API-PASSPHRASE')

    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KC-API-KEY'] = config('KC-API-KEY')
    headers['KC-API-KEY-VERSION'] = '2'
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 params_str.encode('utf-8'),
                 hashlib.sha256).digest()
    )
    headers['KC-API-PASSPHRASE'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 _secret_passphrase .encode('utf-8'),
                 hashlib.sha256).digest())

    if http_method in ['POST']:
        headers['Content-Type'] = "application/json"

    return headers


def add_sign_kucoin_futures(params_str, timestamp, http_method):
    headers = {}
    _secret_key = config('KC-SECRET-KEY-FUT', default='')
    _secret_passphrase = config('KC-API-PASSPHRASE-FUT', default='')

    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KC-API-KEY'] = config('KC-API-KEY-FUT', default='')
    headers['KC-API-KEY-VERSION'] = config('KC-API-KEY-VERSION-FUT', default='')
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 params_str.encode('utf-8'),
                 hashlib.sha256).digest()
    )
    headers['KC-API-PASSPHRASE'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 _secret_passphrase.encode('utf-8'),
                 hashlib.sha256).digest())

    if http_method in ['POST']:
        headers['Content-Type'] = "application/json"

    return headers


def kucoin_send_signed_request(http_method, url_path, **kwargs):
    timestamp = get_timestamp()

    if kwargs.get('futures'):
        url = KUCOIN_FUTURES_BASE_URL + url_path
        add_sign_kucoin = add_sign_kucoin_futures
    else:
        url = KUCOIN_SPOT_BASE_URL + url_path
        add_sign_kucoin = add_sign_kucoin_spot

    data = kwargs.pop('data', {})

    str_to_sign = str(timestamp) + http_method + url_path
    data_json = json.dumps(data)

    if http_method in ('GET', 'DELETE'):
        headers = add_sign_kucoin(str_to_sign, timestamp, http_method)
        response = requests.request('get', url, headers=headers)
        return response.json().get('data')
    if http_method in ('POST', 'PUT'):
        str_to_sign += data_json
        headers = add_sign_kucoin(str_to_sign, timestamp, http_method)
        response = requests.request(http_method, url, headers=headers, json=data, data=data_json)
        return response.json().get('data')

