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

    @classmethod
    def get_withdraw_channel(cls, channel) -> 'FiatWithdraw':
        mapping = {
            FiatWithdrawRequest.PAYIR: PayirChanel,
            FiatWithdrawRequest.ZIBAL: ZibalChanel
        }
        return mapping[channel]()

    def get_wallet_id(self) -> int:
        raise NotImplementedError

    def get_wallet_data(self, wallet_id: int):
        raise NotImplementedError

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> str:
        raise NotImplementedError

    def get_withdraw_status(self, request_id: int, provider_id: str) -> int:
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

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> str:
        data = self.collect_api('/api/v2/cashouts', method='POST', data={
            'walletId': wallet_id,
            'amount': amount * 10,
            'name': receiver.user.get_full_name(),
            'iban': receiver.iban[2:],
            'uid': request_id,
        })

        return str(data['cashout']['id'])

    def get_withdraw_status(self, request_id: int, provider_id: str) -> str:
        data = self.collect_api(f'/api/v2/cashouts/track/{request_id}')

        mapping_status = {
           3: self.CANCELED,
           4: self.DONE,
           5: self.CANCELED

        }
        status = data['cashout']['status']
        return mapping_status.get(int(status), self.PENDING)


class ZibalChanel(FiatWithdraw):

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
            id=wallet_id,
            name=data['name'],
            balance=data['balance'] // 10,
            free=data['withdrawableBalance'] // 10
        )

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> str:
        data = self.collect_api('/v1/wallet/checkout/plus', method='POST', data={
            'id': wallet_id,
            'amount': amount * 10,
            'bankAccount': receiver.iban,
            'uniqueCode': request_id
        })

        return data['id']

    def get_withdraw_status(self, request_id: int, provider_id: str) -> int:
        data = self.collect_api(f'/v1/report/checkout/inquire', method='POST', data={
            "checkoutRequestId": '2649446'
        })

        mapping_status = {
            "0": self.DONE,
            "1": self.CANCELED,
            "2": self.CANCELED,
        }
        status = data['details'].get('checkoutStatus', self.PENDING)
        return mapping_status.get(status, self.PENDING)
