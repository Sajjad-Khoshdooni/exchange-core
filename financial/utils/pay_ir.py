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


class Payir:
    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None) -> dict:

        url = 'https://pay.ir' + path

        request_kwargs = {
            'url': url,
            'timeout': 60,
            'headers': {'Authorization': 'Bearer ' + secret('PAY_IR_TOKEN')},
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
        data = cls.collect_api(f'/api/v2/wallets/{wallet_id}')['wallet']

        return Wallet(
            id=data['id'],
            name=data['name'],
            balance=data['balance'] // 10,
            free=data['cashoutableAmount'] // 10
        )

    @classmethod
    def withdraw(cls, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> int:
        data = cls.collect_api('/api/v2/cashouts', method='POST', data={
            'walletId': wallet_id,
            'amount': amount * 10,
            'name': receiver.user.get_full_name(),
            'iban': receiver.iban,
            'uid': request_id,
        })

        return data['id']

    @classmethod
    def get_withdraw_status(cls, withdraw_id: int) -> int:
        data = cls.collect_api(f'/api/v2/cashouts/{withdraw_id}')
        return data['status']
