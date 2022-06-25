import logging
from dataclasses import dataclass

import requests
from yekta_config import secret
from yekta_config.config import config

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

    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'

    WITHDRAW_CHANNEL = config('WITHDRAW_CHANNEL')

    @classmethod
    def get_withdraw_chanel(cls, chanel=None):
        maping = {
            FiatWithdrawRequest.PAYIR: PayirChanel,
            FiatWithdrawRequest.ZIBAL: ZiblaChanel
        }
        if chanel:
            return maping[chanel]()
        else:
            return maping[cls.WITHDRAW_CHANNEL]()

    def get_wallet_id(self):
        raise NotImplementedError

    def get_wallet_data(self, wallet_id: int):
        raise NotImplementedError

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int):
        raise NotImplementedError

    def get_withdraw_status(self, request_id: int) -> int:
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
    def get_withdraw_status(cls, request_id: int) -> str:
        data = cls.collect_api(f'/api/v2/cashouts/track/{request_id}')

        maping_status = {
           3: cls.CANCELED,
           4: cls.DONE,
           5: cls.CANCELED

        }
        status = data['cashout']['status']
        return maping_status.get(int(status), cls.PENDING)


class ZiblaChanel(FiatWithdraw):

    def get_wallet_id(self):
        return config('ZIBAL_WALLET_ID', cast=int)

    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None) -> dict:

        url = 'https://api.zibal.ir' + path

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
            logger.error('zibal connection error', extra={
                'url': url,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        resp_data = resp.json()

        if not resp_data['result'] == 1:
            raise ServerError

        return resp_data['data']

    def get_wallet_data(self, wallet_id: int) -> Wallet:
        data = self.collect_api(f'/v1/wallet/balance', method='POST', data={
            "id": wallet_id
        })

        return Wallet(
            id=data['id'],
            name=data['name'],
            balance=data['balance'] // 10,
            free=data['withdrawableBalance'] // 10
        )

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> int:
        data = self.collect_api('/v1/wallet/checkout', method='POST', data={
            'amount': amount * 10,
            'id': wallet_id,
            'bankAcount': receiver.iban[2:],
            "checkoutDelay": 0,
            'description': receiver.user.get_full_name(),
        })

        return data['id']

    @classmethod
    def get_withdraw_status(cls, request_id: int) -> int:
        data = cls.collect_api(f'/v1/report/checkout/inquire/', method='POST', data={
            "checkoutRequestId": request_id
        })

        maping_status = {
            "1": cls.CANCELED,
            "0": cls.DONE,
        }
        status = data['checkoutStatus']
        return maping_status.get(status, cls.PENDING)
