from accounts.models import User, FinotechRequest
from accounts.verifiers.finotech import ServerError
from accounts.verifiers.jibit import Response
from decouple import config
from urllib3.exceptions import ReadTimeoutError
import requests
import logging

logger = logging.getLogger(__name__)


# todo : refactor Jibit & Zibal requesters
class ZibalRequester:
    BASE_URL = 'https://api.zibal.ir'

    def __init__(self, user: User):
        self._user = user

    def _get_cc_token(self):
        # return config('ZIBAL_API_TOKEN')
        return '65173c72e07a4b718f4e7423cb2a3ac8'

    def collect_api(self, path: str, method: str = 'GET', data=None, weight: int = 0) -> Response:
        if data is None:
            data = {}

        token = self._get_cc_token()

        url = self.BASE_URL + path

        req_object = FinotechRequest(
            url=url,
            method=method,
            data=data,
            user=self._user,
            service=FinotechRequest.JIBIT,
            weight=weight,
        )

        request_kwargs = {
            'url': url,
            'timeout': 30,
            'headers': {'Authorization': 'Bearer ' + token},
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
            req_object.save(update_fields=['response', 'status_code'])

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

        return Response(data=resp_data, status_code=resp.ok)

    def matching(self, phone_number: str = None, national_code: str = None) -> Response:
        params = {
            "mobile": phone_number,
            "nationalCode": national_code
        }

        return self.collect_api(
            data=params,
            path='/v1/facility/shahkarInquiry',
            method='POST',
            weight=FinotechRequest.JIBIT_ADVANCED_MATCHING if national_code else FinotechRequest.JIBIT_SIMPLE_MATCHING
        )

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
