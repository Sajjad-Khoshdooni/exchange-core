import logging
from dataclasses import dataclass

import requests
from django.utils import timezone
from yekta_config import secret
from yekta_config.config import config

from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from financial.models import BankAccount, FiatWithdrawRequest

logger = logging.getLogger(__name__)


class ServerError(Exception):
    pass


@dataclass
class Wallet:
    id: int
    name: str
    balance: int
    free: int


class FiatWithdraw:

    ZIBAL = 'zibal'
    PAY_IR = 'pay_ir'

    WITHDRAW_CHANEL = config('WITHDRAW_CHANEL')

    def get_withdraw_chanel(self):
        maping = {
            self.PAY_IR: PayirChanel,
            self.ZIBAL: ZiblaChanel
        }
        self.__class__ = maping[self.WITHDRAW_CHANEL]
        return self

    def get_wallet_id(self):
        raise NotImplementedError

    def get_wallet_data(self, wallet_id: int):
        raise NotImplementedError

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int):
        raise NotImplementedError


class PayirChanel(FiatWithdraw):

    def get_wallet_id(self):
        return config('PAY_IR_WALLET_ID', cast=int)


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

    def get_wallet_data(self, wallet_id: int) -> Wallet:
        data = self.collect_api(f'/api/v2/wallets/{wallet_id}')['wallet']

        return Wallet(
            id=data['id'],
            name=data['name'],
            balance=data['balance'] // 10,
            free=data['cashoutableAmount'] // 10
        )

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> int:
        data = self.collect_api('/api/v2/cashouts', method='POST', data={
            'walletId': wallet_id,
            'amount': amount * 10,
            'name': receiver.user.get_full_name(),
            'iban': receiver.iban[2:],
            'uid': request_id,
        })

        return data['cashout']['id']

    @classmethod
    def get_withdraw_status(cls, request_id: int) -> int:
        data = cls.collect_api(f'/api/v2/cashouts/track/{request_id}')
        return data['cashout']['status']


class ZiblaChanel(FiatWithdraw):

    def get_wallet_id(self):
        return config('ZIBAL_WALLET_ID', cast=int)
