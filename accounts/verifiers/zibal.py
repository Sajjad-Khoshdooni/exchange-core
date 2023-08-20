from accounts.models import User, FinotechRequest
from accounts.verifiers.finotech import ServerError
from accounts.verifiers.jibit import Response
from accounts.verifiers.basic_verifier import MatchingData

from decouple import config
from urllib3.exceptions import ReadTimeoutError
import requests
import logging

logger = logging.getLogger(__name__)


class ZibalRequester:
    BASE_URL = 'https://api.zibal.ir'

    RESULT_MAP = {
        1: 'SUCCESSFUL',
        2: 'INVALID_API_KEY',
        3: 'WRONG_API_KEY',
        4: 'PERMISSION_DENIED',
        5: 'INVALID_CALL_BACK_URL',
        6: 'INVALID_DATA',
        7: 'INVALID_IP',
        8: 'INACTIVE_API_KEY',
        9: 'LOWER_THAN_MINIMUM_AMOUNT',
        21: 'INVALID_IBAN',
        29: 'OUT_OF_STOCK',
        44: 'IBAN_NOT_FOUND',
        45: 'SERVICE_UNAVAILABLE'
    }

    def __init__(self, user: User):
        self._user = user

    def collect_api(self, path: str, method: str = 'GET', data=None, weight: int = 0) -> Response:
        if data is None:
            data = {}

        url = self.BASE_URL + path

        req_object = FinotechRequest(
            url=url,
            method=method,
            data=data,
            user=self._user,
            service=FinotechRequest.ZIBAL,
            weight=weight,
        )

        request_kwargs = {
            'url': url,
            'timeout': 30,
            'headers': {'Authorization':  config('ZIBAL_KYC_API_TOKEN')},
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)

        except (requests.exceptions.ConnectionError, ReadTimeoutError, requests.exceptions.Timeout):
            req_object.response = 'timeout'
            req_object.status_code = 100
            req_object.save()

            logger.error('zibal connection error', extra={
                'path': path,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        resp_data = resp.json()
        req_object.response = resp_data
        req_object.status_code = resp.status_code
        req_object.save()

        if resp.status_code >= 500:
            logger.error('failed to call zibal', extra={
                'path': path,
                'method': method,
                'data': data,
                'resp': resp_data,
                'status': resp.status_code
            })
            raise ServerError

        return Response(data=resp_data, status_code=resp.ok, service='ZIBAL')

    def matching(self, phone_number: str = None, national_code: str = None) -> Response:
        params = {
            "mobile": phone_number,
            "nationalCode": national_code
        }

        resp = self.collect_api(
            data=params,
            path='/v1/facility/shahkarInquiry',
            method='POST',
            weight=FinotechRequest.JIBIT_ADVANCED_MATCHING if national_code else FinotechRequest.JIBIT_SIMPLE_MATCHING
        )
        data = resp.data
        resp.data = MatchingData(is_matched=data['data']['matched'], code=ZibalRequester.RESULT_MAP[data['result']])
        return resp

    def get_iban_info(self, iban: str) -> Response:
        params = {
            "IBAN": iban,
        }
        return self.collect_api(
            data=params,
            path='/v1/facility/ibanInquiry',
            method='POST',
            weight=FinotechRequest.JIBIT_IBAN_INFO_WEIGHT,
        )

    def get_card_info(self, card_pan: str) -> Response:
        params = {
            "cardNumber": card_pan,
        }
        return self.collect_api(
            path='/v1/facility/cardInquiry',
            method='POST',
            data=params,
            weight=FinotechRequest.JIBIT_CARD_INFO_WEIGHT
        )
