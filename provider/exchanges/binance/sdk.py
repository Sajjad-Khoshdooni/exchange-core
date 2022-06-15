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

kucoin_session = requests.Session()
kucoin_session.headers = {
    'KC-API-KEY': secret(f'kucoin-api-key', default=''),
    'KC-API-KEY-VERSION': config(f'kucoin-api-version', default=''),
}

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

def add_sign_kucoin(headers, params_str):
    _secret_key = secret(f'kucoin-secret-key', default='')
    _passphrase_key = secret(f'kucoin-passphrase-key', default='')
    headers['KC-API-SIGN'] = base64.b64encode(
        hmac.new(_secret_key.encode('utf-8'), params_str.encode('utf-8'), hashlib.sha256).digest()
    )
    headers['KC-API-PASSPHRASE'] = _passphrase_key
    return headers


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    api_key = secret('BINANCE_API_KEY', default='')

    session = requests.Session()
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
    _session = kucoin_session
    kucoin_session.headers = {
        'KC-API-KEY': secret(f'kucoin-api-key', default=''),
        'KC-API-KEY-VERSION': config(f'kucoin-api-version', default=''),
    }
    data =kwargs.pop('data', {})
    timestamp = get_timestamp()

    headers = kwargs.get('headers', {}) or {}
    headers['KC-API-TIMESTAMP'] = str(timestamp)

    if http_method in ('GET', 'DELETE'):
        query_params = f'?{"&".join(map(lambda i: f"{i[0]}={i[1]}", data.items()))}' if data else ''
        params_str = f'{timestamp}{http_method.upper()}{url_path}{query_params}'
        kwargs['headers'] = add_sign_kucoin(headers, params_str)
        url = KUCOIN_SPOT_BASE_URL + url_path
        if http_method == 'GET':
            response: requests.Response = requests.session().get(url, **kwargs, timeout=15)

        # response = super(KucoinHandler, cls).collect_api(endpoint, method=method, session=cls._session, params=data,
        #                                                  **kwargs)
        return response


def kucoin_futures_send_public_request():
    pass


def kucoin_futures_send_sined_request():
    pass
