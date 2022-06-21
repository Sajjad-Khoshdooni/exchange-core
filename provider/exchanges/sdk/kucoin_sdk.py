import base64
import hashlib
import hmac

import requests
from django.conf import settings
from rest_framework.utils import json
from yekta_config.config import config

from provider.exchanges.sdk.binance_sdk import get_timestamp

if not settings.DEBUG:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = ''
else:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
        # " https://openapi-sandbox.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = ''


def kucoin_spot_send_public_request(endpoint, method='POST', **kwargs):
    pass


def add_sign_kucoin(params_str, timestamp, http_method):
    headers = {}
    _secret_key = config('KUCOIN_SECRET_KEY', default='')
    _secret_passphrase = config('KC-API-PASSPHRASE', default='')

    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KC-API-KEY'] = config('KC-API-KEY', default='')
    headers['KC-API-KEY-VERSION'] = config('KC-API-KEY-VERSION', default='')
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


def kucoin_spot_send_signed_request(http_method, url_path, **kwargs):
    timestamp = get_timestamp()

    if kwargs.get('futures'):
        url = KUCOIN_FUTURES_BASE_URL + url_path
    else:
        url = KUCOIN_SPOT_BASE_URL + url_path

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

