import base64
import hashlib
import hmac

import requests
from django.conf import settings
from rest_framework.utils import json
from yekta_config import secret
from yekta_config.config import config

from provider.exchanges.sdk.binance_sdk import get_timestamp, create_provider_request_and_log
from provider.models import ProviderRequest

if not settings.DEBUG:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = "https://api-futures.kucoin.com"
else:
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL = "https://api-futures.kucoin.com"


def kucoin_spot_send_public_request(endpoint, method='POST', **kwargs):
    raise NotImplementedError


def add_sign_kucoin_spot(params_str, timestamp, http_method):
    headers = {}
    _secret_key = secret('KUCOIN_SECRET_KEY')
    _secret_passphrase = secret('KUCOIN_PASSPHRASE')

    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KUCOIN_API_KEY'] = config('KUCOIN_API_KEY')
    headers['KUCOIN_API_KEY-VERSION'] = '2'
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 params_str.encode('utf-8'),
                 hashlib.sha256).digest()
    )
    headers['KUCOIN_PASSPHRASE'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 _secret_passphrase .encode('utf-8'),
                 hashlib.sha256).digest())

    if http_method in ['POST']:
        headers['Content-Type'] = "application/json"

    return headers


def add_sign_kucoin_futures(params_str, timestamp, http_method):
    headers = {}
    _secret_key = config('KUCOIN_FUTURES_SECRET_KEY', default='')
    _secret_passphrase = config('KUCOIN_FUTURES_PASSPHRASE', default='')

    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KUCOIN_API_KEY'] = config('KUCOIN_FUTURES_API_KEY', default='')
    headers['KUCOIN_API_KEY-VERSION'] = '2'
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 params_str.encode('utf-8'),
                 hashlib.sha256).digest()
    )
    headers['KUCOIN_PASSPHRASE'] = base64.b64encode(
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
        response = requests.request('GET', url, headers=headers)
    elif http_method in ('POST', 'PUT'):
        str_to_sign += data_json
        headers = add_sign_kucoin(str_to_sign, timestamp, http_method)
        response = requests.request(http_method, url, headers=headers, json=data, data=data_json)
    else:
        raise NotImplementedError

    return create_provider_request_and_log(
        name=ProviderRequest.KUCOIN,
        response=response,
        url=url_path,
        method=http_method,
        data=data
    ).get('data')
