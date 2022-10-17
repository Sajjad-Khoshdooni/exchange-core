import hashlib
import hmac
import logging
import os
import time
from urllib.parse import urlencode

import requests
from decouple import config
from django.conf import settings
from yekta_config import secret

from provider.models import ProviderRequest

logger = logging.getLogger(__name__)

TIMEOUT = 30


if not settings.DEBUG_OR_TESTING:
    BINANCE_SPOT_BASE_URL = "https://api.binance.com"
    BINANCE_FUTURES_BASE_URL = 'https://fapi.binance.com'
else:
    BINANCE_SPOT_BASE_URL = 'https://testnet.binance.vision'
    BINANCE_FUTURES_BASE_URL = "https://testnet.binancefuture.com"


def create_provider_request_and_log(name: str, response, url: str, method: str, data: dict):

    resp_data = response.json()

    if not response.ok:
        print('resp_data')
        print(resp_data)

        ProviderRequest.objects.create(
            name=name,
            url=url,
            data=data,
            method=method,
            response=resp_data,
            status_code=response.status_code
        )

        logger.warning(
            'provider request failed',
            extra={
                'provider_name': name,
                'url': url,
                'method': method,
                'payload': data,
                'status': response.status_code,
                'resp': resp_data
            }
        )

        return
    else:
        if method == 'POST':
            ProviderRequest.objects.create(
                name=name,
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


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(http_method):
    api_key = secret('BINANCE_API_KEY', default='')

    session = requests.Session()
    session.headers.update(
        {"Content-Type": "application/json;charset=utf-8", "X-MBX-APIKEY": api_key}
    )
    session.proxies = {
        'https': config('PROVIDER_PROXY_IP', default='localhost') + ':3128',
        'http': config('PROVIDER_PROXY_IP', default='localhost') + ':3128',
        'ftp': config('PROVIDER_PROXY_IP', default='localhost') + ':3128',
    }

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

    return create_provider_request_and_log(
        name=ProviderRequest.BINANCE,
        response=response,
        url=url_path,
        method=http_method,
        data=payload,
    )


# used for sending public data request
def binance_spot_send_public_request(url_path: str, payload: dict):
    query_string = urlencode(payload, True)
    url = BINANCE_SPOT_BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string
    print("{}".format(url))
    response = dispatch_request("GET")(url=url, timeout=TIMEOUT)

    return create_provider_request_and_log(
        name=ProviderRequest.BINANCE,
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

    return create_provider_request_and_log(
        name=ProviderRequest.BINANCE,
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
    return create_provider_request_and_log(
        name=ProviderRequest.BINANCE,
        response=response,
        url=url_path,
        method='GET',
        data=payload,
    )
