import logging
from dataclasses import dataclass

import requests
from yekta_config import secret
from yekta_config.config import config

from financial.models import BankAccount

logger = logging.getLogger(__name__)


class ServerError(Exception):
    pass


@dataclass
class Wallet:
    id: int
    name: str
    balance: int
    free: int


class Zibal:
    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None) -> dict:

        url = 'https://api.zibal.ir/' + path

        request_kwargs = {
            'url': url,
            'timeout': 60,
            'headers': {'Authorization': 'Bearer ' + secret('ZIBAL_TOKEN')},
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
                resp = method_prop(json=data, **request_kwargs)
        except requests.exceptions.ConnectionError:
            logger.error('pay.ir connection error', extra={
                'url': url,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        resp_data = resp.json()

        if not resp.ok or not resp_data['success']:
            raise ServerError

        return resp_data['data']

    @classmethod
    def get_wallet_data(cls, wallet_id: int) -> Wallet:
        resp = cls.collect_api('v1/wallet/balance/', method='POST', data={
            'id': wallet_id
        })

        data = resp.json()['data']
        return Wallet(
            id=data['id'],
            name=data['name'],
            balance=data['balance'] // 10,
            free=data['withdrawableBalance'] // 10
        )

    @classmethod
    def withdraw(cls, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> int:
        data = cls.collect_api('v1/wallet/checkout', method='POST', data={
            'amount': amount * 10,
            'id': wallet_id,
            'bankAccount': receiver.iban[2:],
            'checkoutDelay': 0,
            'description': receiver.user.get_full_name(),
            'uniqueCode': request_id,
        })

        return data['id']
