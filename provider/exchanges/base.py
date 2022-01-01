import json
import logging
from urllib.parse import urlencode

import requests
from rest_framework import status


logger = logging.getLogger(__name__)


def get_response_detail(resp_json, return_status, status_code):
    return (resp_json, status_code) if return_status else resp_json


class JsonResponse:

    @staticmethod
    def get_json_resp(url: str, session: requests.Session, method='GET', url_kwargs=None, query_params=None,
                      return_status=False, **kwargs):
        complete_url = url
        if url_kwargs:
            complete_url = url.format(**url_kwargs)
        if query_params:
            complete_url += '?' + urlencode(query_params)

        try:
            if method == 'GET':
                resp: requests.Response = session.get(url, **kwargs, timeout=150)
            elif method == 'POST':
                resp: requests.Response = session.post(url, **kwargs, timeout=150)
            elif method == 'PATCH':
                resp: requests.Response = session.patch(url, **kwargs, timeout=150)
            elif method == 'PUT':
                resp: requests.Response = session.put(url, **kwargs, timeout=150)
            else:
                return get_response_detail(None, return_status, None)
            if method == 'GET':
                if not resp.ok:
                    logger.error('failed to fetch data from api endpoint: %s, %s', url, resp.reason, extra={
                        'response': resp.content,
                        'request': kwargs.get('json')
                    })
                    logger.warning('response content: ' + str(resp.content))
                    return get_response_detail(None, return_status, resp.status_code)
            else:
                if not resp.ok:
                    logger.error('failed to post data to api endpoint: %s, %s', url, resp.reason, extra={
                        'response': resp.content,
                        'request': kwargs.get('json'),
                        'headers': resp.headers,
                        'status': resp.status_code
                    })
                    logger.warning('response content: ' + str(resp.content))
                    return get_response_detail(None, return_status, resp.status_code)
            try:
                parsed_json = resp.json()
                if type(parsed_json) == dict:
                    response_internal_status = parsed_json.get('status')
                    if response_internal_status and response_internal_status == 'failed':
                        logger.error('failed to post data to api endpoint: %s, %s', url, response_internal_status, extra={
                            'response': resp.content,
                            'request': kwargs.get('json'),
                            'headers': resp.headers,
                            'status': resp.status_code
                        })
                        return get_response_detail(None, return_status, status.HTTP_400_BAD_REQUEST)
                return get_response_detail(parsed_json, return_status, resp.status_code)
            except json.JSONDecodeError as e:
                logger.error(
                    'failed to decode response from api endpoint: %s', url, extra={
                        'exception': str(e)
                    }
                )
            return get_response_detail(None, return_status, resp.status_code)
        except requests.exceptions.ConnectionError as e:
            logger.error('connection error while requesting api endpoint: %s', url, extra={
                'request': kwargs.get('json'),
                'exception': str(e)
            })
            return get_response_detail(None, return_status, None)
        except Exception as e:
            logger.error('unknown exception while requesting from api endpoint: %s', url, extra={
                'request': kwargs.get('json'),
                'exception': str(e)
            })
            return get_response_detail(None, return_status, None)


class BaseExchangeHandler:
    _base_api_url = None
    _session = None

    api_path = None
    exchange = None

    @classmethod
    def collect_api(cls, endpoint, method='POST', **kwargs):
        if not cls._base_api_url:
            raise Exception('_base_api_url is empty')
        return JsonResponse.get_json_resp(cls._base_api_url + endpoint, cls._session, method=method, **kwargs)

    @classmethod
    def place_order(cls, symbol, order_type, amount, price, **kwargs):
        raise NotImplementedError()

