import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests
from yekta_config import secret
from yekta_config.config import config

from provider.exchanges.sdk.binance_sdk import create_provider_request_and_log
from provider.models import ProviderRequest

MEXC_SPOT_BASE_URL = 'https://api.mexc.com'
API_KEY = config('MEXC_API_KEY')
SECRET_KEY = secret('MEXC_SECRET_KEY')


def get_time_stamp():
    return int(time.time() * 1000)


def hashing(query_string):
    secret_key = SECRET_KEY
    return hmac.new(secret_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def mexc_send_sign_request(http_method: str, url_path: str, payload: dict):

    query_string = urlencode(payload, True)

    header = {'X-MEXC-APIKEY': API_KEY, 'Content-Type': 'application/json'}
    if query_string:
        query_string = '{}&recvWindow=50000&timestamp={}'.format(query_string, get_time_stamp())
    else:
        query_string = 'recvWindow=50000&timestamp={}'.format(get_time_stamp())
    url = MEXC_SPOT_BASE_URL + url_path + '?' + query_string + "&signature=" + hashing(query_string)

    response = requests.request(method=http_method, url=url, headers=header)

    return create_provider_request_and_log(
        name=ProviderRequest.MEXC,
        response=response,
        url=url_path,
        method=http_method,
        data=payload
    )


def mexc_send_public_request(http_method: str, url_path: str, payload: dict):

    query_string = urlencode(payload, True)

    header = {'X-MEXC-APIKEY': API_KEY, 'Content-Type': 'application/json'}
    url = MEXC_SPOT_BASE_URL + url_path
    if query_string:
        query_string = '{}'.format(query_string)
        url = url + '?' + query_string

    response = requests.request(method=http_method, url=url, headers=header)

    return create_provider_request_and_log(
        name=ProviderRequest.MEXC,
        response=response,
        url=url_path,
        method=http_method,
        data=payload
    )
