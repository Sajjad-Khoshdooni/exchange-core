import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union

import pytz
import requests
from django.core.cache import caches
from django.utils import timezone
from yekta_config import secret
from yekta_config.config import config

from financial.models import BankAccount, FiatWithdrawRequest, Gateway, Payment, PaymentRequest
from financial.utils.withdraw_limit import is_holiday, time_in_range

logger = logging.getLogger(__name__)


class ServerError(Exception):
    pass


class ProviderError(Exception):
    pass


@dataclass
class Wallet:
    id: int
    name: str
    balance: int
    free: int


@dataclass
class Withdraw:
    tracking_id: str
    status: str
    receive_datetime: Union[datetime, None]
    message: str = ''


class FiatWithdraw:

    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'

    @classmethod
    def get_withdraw_channel(cls, channel) -> 'FiatWithdraw':
        mapping = {
            FiatWithdrawRequest.PAYIR: PayirChannel,
            FiatWithdrawRequest.ZIBAL: ZibalChannel,
            FiatWithdrawRequest.ZARINPAL: ZarinpalChannel,
            FiatWithdrawRequest.JIBIT: JibitChannel
        }
        return mapping[channel]()

    def get_wallet_id(self) -> int:
        raise NotImplementedError

    def get_wallet_data(self, wallet_id: int):
        raise NotImplementedError

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> Withdraw:
        raise NotImplementedError

    def get_withdraw_status(self, request_id: int, provider_id: str) -> str:
        raise NotImplementedError

    def get_estimated_receive_time(self, created: datetime):
        raise NotImplementedError

    def get_total_wallet_irt_value(self):
        raise NotImplementedError

    def is_active(self):
        return True

    def update_missing_payments(self, gateway: Gateway):
        pass


class PayirChannel(FiatWithdraw):

    def get_wallet_id(self):
        return config('PAY_IR_WALLET_ID', cast=int)

    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None, verbose: bool = True, timeout: float = 30) -> dict:

        url = 'https://pay.ir' + path

        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': 'Bearer ' + secret('PAY_IR_TOKEN')},
            # 'proxies': {
            #     'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            # }
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

        if verbose:
            print('status', resp.status_code)
            print('data', resp_data)

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

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> Withdraw:
        data = self.collect_api('/api/v2/cashouts', method='POST', data={
            'walletId': wallet_id,
            'amount': amount * 10,
            'name': receiver.user.get_full_name(),
            'iban': receiver.iban[2:],
            'uid': request_id,
        })

        return Withdraw(
            tracking_id=str(data['cashout']['id']),
            status=FiatWithdrawRequest.PENDING,
            receive_datetime=self.get_estimated_receive_time(timezone.now())
        )

    def get_withdraw_status(self, request_id: int, provider_id: str) -> str:
        data = self.collect_api(f'/api/v2/cashouts/track/{request_id}')

        mapping_status = {
           3: self.CANCELED,
           4: self.DONE,
           5: self.CANCELED

        }
        status = data['cashout']['status']
        return mapping_status.get(int(status), self.PENDING)

    def get_estimated_receive_time(self, created: datetime):
        request_date = created.astimezone()
        request_time = request_date.time()
        receive_time = request_date.replace(microsecond=0)

        if is_holiday(request_date):

            if time_in_range('00:00', '10:00', request_time):
                receive_time = receive_time.replace(hour=15, minute=00, second=00)
            else:
                receive_time += timedelta(days=1)

                if is_holiday(receive_time):
                    receive_time = receive_time.replace(hour=15, minute=00, second=00)
                else:
                    receive_time = receive_time.replace(hour=10, minute=30, second=00)

        else:
            if time_in_range('0:0', '0:30', request_time):
                receive_time = receive_time.replace(hour=10, minute=30, second=00)

            elif time_in_range('0:30', '10:30', request_time):
                receive_time = receive_time.replace(hour=14, minute=30, second=00)

            elif time_in_range('10:30', '13:23', request_time):
                receive_time = receive_time.replace(hour=19, minute=30, second=00)

            elif time_in_range('13:23', '18:30', request_time):
                receive_time += timedelta(days=1)
                receive_time = receive_time.replace(hour=4, minute=30, second=00)

            else:
                receive_time += timedelta(days=1)

                if is_holiday(receive_time):
                    receive_time = receive_time.replace(hour=14, minute=30, second=00)
                else:
                    receive_time = receive_time.replace(hour=10, minute=30, second=00)

        return receive_time

    def get_total_wallet_irt_value(self):
        resp = self.collect_api(
            path='/api/v2/wallets',
            timeout=5
        )

        total_wallet_irt_value = 0
        for wallet in resp['wallets']:
            total_wallet_irt_value += Decimal(wallet['balance'])

        return total_wallet_irt_value // 10

    def is_active(self):
        return bool(config('PAY_IR_TOKEN', ''))


class ZibalChannel(FiatWithdraw):
    def get_wallet_id(self):
        return config('ZIBAL_WALLET_ID', cast=int)

    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None, timeout: float = 30) -> dict:

        url = 'https://api.zibal.ir' + path

        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': 'Bearer ' + secret('ZIBAL_TOKEN')},
            # 'proxies': {
            #     'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            # }
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
            print(resp_data)
            raise ServerError(resp_data)

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

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> Withdraw:
        paya_banks = ['AYANDEH']

        if receiver.bank not in paya_banks:
            checkout_delay = -1
            status = FiatWithdrawRequest.DONE
        else:
            checkout_delay = 0
            status = FiatWithdrawRequest.PENDING

        try:
            data = self.collect_api('/v1/wallet/checkout/plus', method='POST', data={
                'id': wallet_id,
                'amount': amount * 10,
                'bankAccount': receiver.iban,
                'uniqueCode': request_id,
                'wageFeeMode': 2,
                'checkoutDelay': checkout_delay,
                'showTime': True
            })
        except ServerError as e:
            resp = e.args[0]
            message = resp.get('message', '')

            if 'این درخواست تسویه قبلا ثبت شده است' in message:
                return Withdraw(
                    tracking_id='',
                    status=FiatWithdrawRequest.PENDING,
                    receive_datetime=timezone.now() + timedelta(hours=3),
                    message=message,
                )
            elif 'این حساب مسدود شده و یا قابلیت واریز ندارد' in message:
                return Withdraw(
                    tracking_id='',
                    status=FiatWithdrawRequest.CANCELED,
                    receive_datetime=None,
                    message=message,
                )
            elif 'باقی مانده سقف روزانه تسویه به این شبا' in message:
                return Withdraw(
                    tracking_id='',
                    status=FiatWithdrawRequest.CANCELED,
                    receive_datetime=None,
                    message=message,
                )
            else:
                raise ProviderError(message)

        receive_datetime = datetime.strptime(data['predictedCheckoutDate'], '%Y/%m/%d-%H:%M:%S')

        return Withdraw(
            tracking_id=data['id'],
            status=status,
            receive_datetime=receive_datetime.replace(tzinfo=pytz.utc).astimezone()
        )

    def get_withdraw_status(self, request_id: int, provider_id: str) -> str:
        data = self.collect_api(f'/v1/report/checkout/inquire', method='POST', data={
            "walletId": self.get_wallet_id(),
            'uniqueCode': str(request_id)
        })

        if data['type'] == 'canceledCheckout':
            return self.CANCELED
        elif data['type'] == 'checkoutQueue':
            return self.PENDING

        mapping_status = {
            0: self.DONE,
            1: self.CANCELED,
            2: self.CANCELED,
        }
        status = data['details'][0].get('checkoutStatus', self.PENDING)
        return mapping_status.get(status, self.PENDING)

    def get_estimated_receive_time(self, created: datetime):
        request_date = created.astimezone()
        request_time = request_date.time()
        receive_time = request_date.replace(microsecond=0, second=0, minute=0)

        if is_holiday(request_date):
            receive_time += timedelta(days=1)
            receive_time.replace(hour=5, minute=0)
        else:
            if time_in_range('0:0', '3:25', request_time):
                receive_time = receive_time.replace(hour=11, minute=30)
            elif time_in_range('3:25', '10:25', request_time):
                receive_time = receive_time.replace(hour=14, minute=30)
            elif time_in_range('10:25', '13:25', request_time):
                receive_time = receive_time.replace(hour=19, minute=30)
            elif time_in_range('13:25', '18:25', request_time):
                receive_time += timedelta(days=1)
                receive_time = receive_time.replace(hour=5, minute=0)

                if is_holiday(receive_time):
                    receive_time += timedelta(days=1)
            else:
                receive_time += timedelta(days=1)
                receive_time = receive_time.replace(hour=11, minute=30)

                if is_holiday(receive_time):
                    receive_time += timedelta(days=1)

        return receive_time

    def get_total_wallet_irt_value(self):
        if not self.is_active():
            return 0

        resp = self.collect_api(
            path='/v1/wallet/list',
            timeout=5
        )

        total_wallet_irt_value = 0
        for wallet in resp:
            total_wallet_irt_value += Decimal(wallet['balance']) + Decimal(wallet.get('pendingPFAmount', 0))

        return total_wallet_irt_value // 10

    def is_active(self):
        return bool(config('ZIBAL_TOKEN', ''))

    def get_transactions(self, merchant_id: str, status: int):
        return self.collect_api(
            path='/v1/gateway/report/transaction',
            method='POST',
            data={'merchantId': merchant_id, 'status': status},
            timeout=120
        )

    def update_missing_payments(self, gateway: Gateway):
        transactions = self.get_transactions(gateway.merchant_id, status=2)

        for t in transactions:
            authority = t['trackId']

            payment_request = PaymentRequest.objects.get(authority=authority)

            payment, _ = Payment.objects.get_or_create(
                payment_request=payment_request
            )

            payment_request.get_gateway().verify(payment)


class ZarinpalChannel(FiatWithdraw):

    def get_total_wallet_irt_value(self):
        return 0


class JibitChannel(FiatWithdraw):
    BASE_URL = ' https://napi.jibit.ir/trf'

    @classmethod
    def _get_token(cls):
        token_cache = caches['token']
        JIBIT_GATEWAY_TRANSFER_TOKEN_KEY = 'jibit_gateway_transfer_token'

        resp = requests.post(
            url=cls.BASE_URL + '/v2/tokens/generate',
            json={
                'apiKey': secret('JIBIT_GATEWAY-API_KEY'),
                'secretKey': secret('JIBIT_GATEWAY_API_SECRET'),
            },
            timeout=30,
            # proxies={
            #     'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            # }
        )

        if resp.ok:
            resp_data = resp.json()
            token = resp_data['accessToken']
            expire = 23 * 3600
            token_cache.set(JIBIT_GATEWAY_TRANSFER_TOKEN_KEY, token, expire)

            return token

    def get_wallet_id(self) -> int:
        return config('JIBIT_WALLET_ID', cast=int)

    @classmethod
    def collect_api(cls, path: str, method: str = 'GET', data: dict = None, verbose: bool = True, timeout: float = 30) ->dict:
        url = 'https://napi.jibit.ir/trf' + path
        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': 'Bearer ' + cls._get_token()},
            # 'proxies': {
            #     'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            #     'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            # }

        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)
        except requests.exceptions.ConnectionError:
            logger.error('jibit connection error', extra={
                'url': url,
                'method': method,
                'data': data,
            })
            raise TimeoutError
        resp_data = resp.json()

        if verbose:
            print('status', resp.status_code)
            print('data', resp_data)

        if not resp.ok or not resp_data['success']:
            raise ServerError

        return resp_data['data']

    def gat_wallet_data(self, wallet_id: int) -> Wallet:
        data = self.collect_api('/v2/balances')
        return Wallet(
            id=wallet_id,
            name='main',
            balance=data['balance'] // 10,
            free=data['settleableBalance'] // 10
        )

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id: int) -> Withdraw:
        self.collect_api('/v2/transfers', method='post', data={
            'submissionMode': 'TRANSFER',
            'transfer': [{
                'transferID': str(request_id),
                'destination': receiver.iban[2:],
                'destinationLastName': receiver.user.get_full_name(),
                'amount': amount,
                'currency': 'TOMAN',
            }],
        })

        return Withdraw(
            tracking_id=str(request_id),
            status=FiatWithdrawRequest.PENDING,
            receive_datetime=self.get_estimated_receive_time(timezone.now())
        )

    def get_withdraw_status(self, request_id: int, provider_id: str) -> str:
        data = self.collect_api('/v2/transfers?transferID={}'.format(request_id))

        mapping_status = {
            'CANCELLED': self.CANCELED,
            'TRANSFERRED': self.DONE,
            'CANCELLING': self.CANCELED,
            'FAILED': self.CANCELED,
            'IN_PROGRESS': self.PENDING
        }

        status = data['transfers'][0]['state']
        return mapping_status.get(status, self.PENDING)

    def get_estimated_receive_time(self, created: datetime):
        request_date = created.astimezone()
        receive_time = request_date.replace(microsecond=0)

        receive_time += timedelta(hours=3)

        return receive_time

    def get_total_wallet_irt_value(self):
        if not self.is_active():
            return 0

        resp = self.collect_api(
            path='/v1/wallet/list',
            timeout=5
        )

        total_wallet_irt_value = 0
        for wallet in resp:
            total_wallet_irt_value += Decimal(wallet['balance']) + Decimal(wallet.get('pendingPFAmount', 0))

        return total_wallet_irt_value // 10

    def is_active(self):
        return False
