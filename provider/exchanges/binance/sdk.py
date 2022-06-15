import base64
import hashlib
import hmac
import logging
import os
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)

TIMEOUT = 30


if not settings.DEBUG:
    BINANCE_SPOT_BASE_URL = "https://api.binance.com"
    BINANCE_FUTURES_BASE_URL = 'https://fapi.binance.com'
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"
    KUCOIN_FUTURES_BASE_URL= "https://api-futures.kucoin.com"
else:
    BINANCE_SPOT_BASE_URL = 'https://testnet.binance.vision'
    BINANCE_FUTURES_BASE_URL = "https://testnet.binancefuture.com"
    KUCOIN_SPOT_BASE_URL = "https://api.kucoin.com"



def create_binance_requset_and_log(response: str, url: str, method: str, data: dict):
    from provider.models import BinanceRequests
    resp_data = response.json()
    if not response.ok:
        print('resp_data')
        print(resp_data)

        logger.warning(
            'binance request failed',
            extra={
                'url': url,
                'method': method,
                'payload': data,
                'status': response.status_code,
                'resp': resp_data
            }
        )

        BinanceRequests.objects.create(
            url=url,
            data=data,
            method=method,
            response=resp_data,
            status_code=response.status_code
        )
        return
    else:
        if method == 'POST':
            BinanceRequests.objects.create(
                url=url,
                data=data,
                method=method,
                response=resp_data,
                status_code=response.status_code
            )
        return resp_data


def hashing(query_string):
    secret_key = os.environ['BIN_SECRET']
    return hmac.new(
        secret_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

def add_sign_kucoin(params_str, timestamp):
    headers = {}
    _secret_key = secret('KUCOIN_SECRET_KEY', default=''),
    _secret_passphrase = secret('KC-API-PASSPHRASE', default=''),
    headers['KC-API-KEY'] = secret(f'KC-API-KEY', default=''),
    headers['KC-API-KEY-VERSION']= config('KC-API-KEY-VERSION', default=''),
    headers['KC-API-TIMESTAMP'] = str(timestamp)
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 params_str.encode('utf-8'),
                 hashlib.sha256).digest()
    )
    headers['KC-API-PASSPHRASE'] =base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'),
                 _secret_passphrase .encode('utf-8'),
                 hashlib.sha256).digest())
    return headers


def get_timestamp():
    return int(time.time() * 1000)

def get_session():
    return requests.session()

def dispatch_request(http_method):
    api_key = secret('BINANCE_API_KEY', default='')

    session = get_session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": api_key}
    )
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


# used for sending request requires the signature
def binance_spot_send_signed_request(http_method, url_path, payload: dict):
    query_string = urlencode(payload, True)

    if query_string:
        query_string = "{}&recvWindow=60000&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "recvWindow=60000&timestamp={}".format(get_timestamp())
    url = (
        BINANCE_SPOT_BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}, "timeout": TIMEOUT}

    response = dispatch_request(http_method)(**params)

    return create_binance_requset_and_log(
        response=response,
        url=url_path,
        method=http_method,
        data=payload
    )


# used for sending public data request
def binance_spot_send_public_request(url_path: str, payload: dict):
    query_string = urlencode(payload, True)
    url = BINANCE_SPOT_BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string
    print("{}".format(url))
    response = dispatch_request("GET")(url=url, timeout=TIMEOUT)
    return create_binance_requset_and_log(
        response=response,
        url=url_path,
        method="GET",
        data=payload
    )


# used for sending request requires the signature
def binance_futures_send_signed_request(http_method: str, url_path: str, payload: dict):
    query_string = urlencode(payload)
    query_string = query_string.replace("%27", "%22")

    if query_string:
        query_string = "{}&recvWindow=60000&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "recvWindow=60000&timestamp={}".format(get_timestamp())

    url = (
        BINANCE_FUTURES_BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}, "timeout": TIMEOUT}

    response = dispatch_request(http_method)(**params)

    return create_binance_requset_and_log(
        response=response,
        url=url_path,
        method=http_method,
        data=payload
    )


# used for sending public data request
def binance_futures_send_public_request(url_path, payload: dict):
    query_string = urlencode(payload, True)
    url = BINANCE_FUTURES_BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string

    print("{}".format(url))

    response = dispatch_request("GET")(url=url, timeout=TIMEOUT)
    return create_binance_requset_and_log(
        response=response,
        url=url_path,
        method='GET',
        data=payload
    )


def kucoin_spot_send_public_request(endpoint, method='POST', **kwargs):


def kucoin_spot_send_signed_request(http_method, url_path, **kwargs):
    timestamp = get_timestamp()

    url = KUCOIN_SPOT_BASE_URL + url_path

    session = get_session()
    session.headers = {
        'KC-API-KEY': secret(f'kucoin-api-key', default=''),
        'KC-API-KEY-VERSION': config(f'kucoin-api-version', default=''),
    }

    data =kwargs.pop('data', {})
    str_to_sign = timestamp + http_method + url_path
    query_params = "?" + urlencode(data)
    if http_method in ('GET', 'DELETE'):


        kwargs['headers'] = add_sign_kucoin(str_to_sign, timestamp)
        if http_method == 'GET':
            response: requests.Response = requests.session().get(url, **kwargs, timeout=15)

        # response = super(KucoinHandler, cls).collect_api(endpoint, method=method, session=cls._session, params=data,
        #                                                  **kwargs)
        return response
    if http_method in ('POST', 'PUT'):
        str_to_sign += query_params
        kwargs['headers'] = add_sign_kucoin(str_to_sign, timestamp)
        response = requests.request(http_method, url, kwargs['headers'] )


def kucoin_futures_send_public_request():
    pass


def kucoin_futures_send_sined_request():
    pass
