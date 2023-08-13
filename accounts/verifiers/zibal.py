from accounts.models import User, FinotechRequest
from accounts.verifiers.finotech import ServerError

from decouple import config
from urllib3.exceptions import ReadTimeoutError
import requests
import logging


from rest_framework.response import Response

logger = logging.getLogger(__name__)

class ZibalRequester:
    BASE_URL = 'https://api.zibal.ir'

    def __init__(self, user: User):
        self._user = User

    def _get_cc_token(self, force_renew: bool = False):
        return config('ZIBAL_API_TOKEN')

    def collect_api(self, path: str, method: str = 'GET', data: dict = {}, weight: int = 0) -> Response:
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
            req_object.save()

            logger.error('jibit connection error', extra={
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

        return Response(data=resp_data, status=resp.ok)

    def matching(self, phone_number: str = None, national_code: str = None) -> Response:
        ...
