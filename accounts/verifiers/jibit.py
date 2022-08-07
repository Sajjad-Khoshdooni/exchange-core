import datetime
import logging

import requests
from django.core.cache import caches
from django.utils import timezone
from urllib3.exceptions import ReadTimeoutError
from yekta_config import secret
from yekta_config.config import config

from accounts.models import FinotechRequest
from accounts.utils.validation import gregorian_to_jalali_date_str
from accounts.verifiers.finotech import ServerError

logger = logging.getLogger(__name__)
token_cache = caches['token']

JIBIT_TOKEN_KEY = 'jibit-token'


class JibitRequester:
    BASE_URL = 'https://napi.jibit.ir/ide'

    def __init__(self, user):
        self._user = user

    def _get_cc_token(self, force_renew: bool = False):
        if not force_renew:
            token = token_cache.get(JIBIT_TOKEN_KEY)
            if token:
                return token

        resp = requests.post(
            url=self.BASE_URL + '/v1/token/generate',
            data={
                'apiKey': secret('JIBIT_API_KEY'),
                'secretKey': secret('JIBIT_API_KEY'),
            },
        )

        if resp.ok:
            resp_data = resp.json()
            token = resp_data['accessToken']
            expire = 24 * 3600

            token_cache.set(JIBIT_TOKEN_KEY, token, expire)

            return token

    def collect_api(self, path: str, method: str = 'GET', data: dict = None, force_renew_token: bool = False,
                    search_key: str = None) -> dict:

        if search_key:
            request = FinotechRequest.objects.filter(
                created__gt=timezone.now() - datetime.timedelta(days=30),
                search_key=search_key,
                service=FinotechRequest.JIBIT
            ).order_by('-created').first()

            if request:

                if request.status_code >= 500:
                    raise ServerError

                if request.status_code not in (200, 201):
                    return

                return request.response

        token = self._get_cc_token()

        if data is None:
            data = {}

        url = self.BASE_URL + path

        req_object = FinotechRequest.objects.create(
            url=url,
            method=method,
            data=data,
            user=self._user,
            service=FinotechRequest.JIBIT
        )

        request_kwargs = {
            'url': url,
            'timeout': 10,
            'headers': {'Authorization': 'Bearer ' + token},
            'proxies': {
                'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
                'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
                'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            }
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(data=data, **request_kwargs)
        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            req_object.response = 'timeout'
            req_object.status_code = 100
            req_object.save()

            logger.error('jibit connection error', extra={
                'path': path,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        if not force_renew_token and resp.status_code == 403:
            return self.collect_api(path, method, data, force_renew_token=True, search_key=search_key)

        resp_data = resp.json()

        req_object.response = resp_data
        req_object.status_code = resp.status_code

        if resp.ok or (resp.status_code == 400 and 'nidVerification' in path):
            req_object.search_key = search_key

        req_object.save()

        if resp.status_code >= 500:
            raise ServerError

        if not resp.ok:
            logger.error('failed to call jibit', extra={
                'path': path,
                'method': method,
                'data': data,
                'resp': resp_data,
                'status': resp.status_code
            })
            print(resp_data)
            return

        return resp_data['result']

    def matching(self, phone_number: str = None, national_code: str = None, full_name: str = None,
                 birth_date: datetime = None, card_pan: str = None, iban: str = None) -> bool:

        if birth_date:
            birth_date = gregorian_to_jalali_date_str(birth_date).replace('/', '')

        params = {
            'mobileNumber': phone_number,
            'nationalCode': national_code,
            'birthDate': birth_date,
            'name': full_name,
            'cardNumber': card_pan,
            'iban': iban,
        }

        key = 'matching-' + '-'.join(map(lambda s: s or '', params.values()))

        params = {k: v for (k, v) in params.items() if v}

        resp = self.collect_api(
            path='/v1/services/matching',
            data=params,
            search_key=key
        )

        if not resp:
            raise ServerError

        return resp['matched']
