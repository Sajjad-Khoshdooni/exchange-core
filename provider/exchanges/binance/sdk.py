import hashlib
import hmac
import logging
import os
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from yekta_config import secret

logger = logging.getLogger(__name__)

TIMEOUT = 30

if not settings.DEBUG:
    SPOT_BASE_URL = "https://api.binance.com"
    FUTURES_BASE_URL = 'https://fapi.binance.com'
else:
    SPOT_BASE_URL = 'https://testnet.binance.vision'
    FUTURES_BASE_URL = "https://testnet.binancefuture.com"


def create_binance_requset_and_log(response, url: str, method: str, data: dict):
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
            response=resp_data
        )
        return
    else:
        if method == 'POST':
            BinanceRequests.objects.create(
                url=url,
                data=data,
                method=method,
                response=resp_data
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
    return {
        "GET": session.get,
        "DELETE": session.delete,
        "PUT": session.put,
        "POST": session.post,
    }.get(http_method, "GET")


# used for sending request requires the signature
def spot_send_signed_request(http_method, url_path, payload: dict):
    query_string = urlencode(payload, True)
    if query_string:
        query_string = "{}&recvWindow=60000&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "recvWindow=60000&timestamp={}".format(get_timestamp())
    url = (
        SPOT_BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}, "timeout": TIMEOUT}

    response = dispatch_request(http_method)(**params)

    return create_binance_requset_and_log(response=response,
                                          url=url_path,
                                          method=http_method,
                                          data=payload
                                          )


# used for sending public data request
def spot_send_public_request(url_path: str, payload: dict):
    query_string = urlencode(payload, True)
    url = SPOT_BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string
    print("{}".format(url))
    response = dispatch_request("GET")(url=url, timeout=TIMEOUT)
    return create_binance_requset_and_log(response=response,
                                          url=url_path,
                                          method="GET",
                                          data=payload
                                          )


# used for sending request requires the signature
def futures_send_signed_request(http_method: str, url_path: str, payload: dict):
    query_string = urlencode(payload)
    query_string = query_string.replace("%27", "%22")

    if query_string:
        query_string = "{}&recvWindow=60000&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = "recvWindow=60000&timestamp={}".format(get_timestamp())

    url = (
        FUTURES_BASE_URL + url_path + "?" + query_string + "&signature=" + hashing(query_string)
    )
    print("{} {}".format(http_method, url))
    params = {"url": url, "params": {}, "timeout": TIMEOUT}

    response = dispatch_request(http_method)(**params)

    return create_binance_requset_and_log(response=response,
                                          url=url_path,
                                          method=http_method,
                                          data=payload
                                          )


# used for sending public data request
def futures_send_public_request(url_path, payload: dict):
    query_string = urlencode(payload, True)
    url = FUTURES_BASE_URL + url_path
    if query_string:
        url = url + "?" + query_string

    print("{}".format(url))

    response = dispatch_request("GET")(url=url, timeout=TIMEOUT)
    return create_binance_requset_and_log(response=response,
                                          url=url_path,
                                          method='GET',
                                          data=payload
                                          )
