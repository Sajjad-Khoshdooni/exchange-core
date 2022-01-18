import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_json_resp(url: str, session: requests.Session, method='GET', **kwargs):

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
            raise NotImplementedError

        if resp.ok:
            return resp.json()
        else:
            logger.error('failed to query to api endpoint: %s, %s', url, resp.reason, extra={
                'method': method,
                'response': resp.content,
                'request': kwargs.get('json')
            })
            # print(url)
            # print(kwargs)
            # print(resp.content)
            return

    except json.JSONDecodeError as e:
        logger.error(
            'failed to decode response from api endpoint: %s', url, extra={
                'exception': str(e)
            }
        )

    except requests.exceptions.ConnectionError as e:
        logger.error('connection error while requesting api endpoint: %s', url, extra={
            'request': kwargs.get('json'),
            'exception': str(e)
        })

    except Exception as e:
        logger.error('unknown exception while requesting from api endpoint: %s', url, extra={
            'request': kwargs.get('json'),
            'exception': str(e)
        })


class BaseExchange:
    _base_api_url = None
    _testnet_api_url = None
    _session = None

    api_path = None
    exchange = None

    MARKET, LIMIT = 'MARKET', 'LIMIT'
    SELL, BUY = 'SELL', 'BUY'
    GET, POST = 'GET', 'POST'

    @classmethod
    def collect_api(cls, endpoint, method='POST', **kwargs):
        if settings.DEBUG:
            base_api = cls._testnet_api_url
        else:
            base_api = cls._base_api_url

        if not base_api:
            raise Exception('_base_api_url is empty')

        return get_json_resp(base_api + endpoint, cls._session, method=method, **kwargs)
