import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from json import JSONDecodeError
from math import log10
from typing import List, Dict, Union

import requests
from decouple import config
from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from pydantic.decorator import validate_arguments
from urllib3.exceptions import ReadTimeoutError

from accounts.verifiers.jibit import Response
from ledger.exceptions import HedgeError
from ledger.models import Asset, Wallet, Transfer
from ledger.utils.cache import get_cache_func_key
from ledger.utils.external_price import SELL, BUY, get_external_price
from ledger.utils.fields import DONE
from ledger.utils.precision import floor_precision

logger = logging.getLogger(__name__)


class MarketMakerRequester:
    def collect_api(self, path: str, method: str = 'GET', data: dict = None, cache_timeout: int = None) -> Response:
        cache_key = None
        if cache_timeout:
            cache_key = 'market_maker:' + get_cache_func_key(self.__class__, path, method, data)
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return Response(data=cached_result)

        result = self._collect_api(path, method, data)

        if cache_timeout and result.success:
            cache.set(cache_key, result.data, cache_timeout)

        return result

    def _collect_api(self, path: str, method: str = 'GET', data: dict = None) -> Response:
        if data is None:
            data = {}

        url = config('MARKET_MAKER_BASE_URL', default='https://maker.raastin.com') + path

        request_kwargs = {
            'url': url,
            'timeout': 60,
            'headers': {'Authorization': config('MARKET_MAKER_TOKEN')},
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)
        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            raise TimeoutError

        try:
            resp_json = resp.json()
        except JSONDecodeError:
            resp_json = None

        return Response(data=resp_json, success=resp.ok, status_code=resp.status_code)

    def get_trade_hedge_info(self, origin_id: str) -> dict:
        resp = self.collect_api(f'/api/v1/trades/{origin_id}/')
        return resp.data


class MockMarketMakerRequester(MarketMakerRequester):
    def get_trade_hedge_info(self, origin_id: str) -> dict:
        return {"origin_id": 26059774, "real_revenue": "0.05919748", "hedge_price": "50000","amount":"8.72000000"}


def get_market_maker_requester() -> MarketMakerRequester:
    if settings.DEBUG_OR_TESTING:
        return MockMarketMakerRequester()
    else:
        return MarketMakerRequester()
