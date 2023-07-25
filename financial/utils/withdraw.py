import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Union

import pytz
import requests
from django.utils import timezone

from accounts.verifiers.jibit import Response
from financial.models import BankAccount, FiatWithdrawRequest, Gateway, PaymentRequest
from financial.utils.ach import next_ach_clear_time
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
    receive_datetime: Union[datetime, None] = None
    message: str = ''


class FiatWithdraw:

    PROCESSING, PENDING, CANCELED, DONE = 'process', 'pending', 'canceled', 'done'

    def __init__(self, gateway: Gateway, verbose: bool = False):
        self.gateway = gateway
        self.verbose = verbose

    @classmethod
    def get_withdraw_channel(cls, gateway: Gateway, verbose: bool = False) -> 'FiatWithdraw':
        mapping = {
            Gateway.PAYIR: PayirChannel,
            Gateway.ZIBAL: ZibalChannel,
            Gateway.ZARINPAL: ZarinpalChannel,
            Gateway.JIBIT: JibitChannel,
            Gateway.JIBIMO: JibimoChannel,
        }
        return mapping[gateway.type](gateway, verbose)

    def get_wallet_data(self, wallet_id: int):
        raise NotImplementedError

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id) -> Withdraw:
        raise NotImplementedError

    def get_withdraw_status(self, request_id: int, provider_id: str) -> Withdraw:
        raise NotImplementedError

    def get_estimated_receive_time(self, created: datetime):
        raise NotImplementedError

    def get_total_wallet_irt_value(self):
        raise NotImplementedError

    def update_missing_payments(self, gateway: Gateway):
        pass

    def is_active(self):
        return bool(self.gateway.withdraw_api_secret_encrypted)


class PayirChannel(FiatWithdraw):

    def collect_api(self, path: str, method: str = 'GET', data: dict = None, timeout: float = 30) -> dict:

        url = 'https://pay.ir' + path

        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': self.gateway.withdraw_api_secret},
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

        if self.verbose:
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

    def get_withdraw_status(self, request_id: int, provider_id: str) -> Withdraw:
        data = self.collect_api(f'/api/v2/cashouts/track/{request_id}')

        mapping_status = {
           3: self.CANCELED,
           4: self.DONE,
           5: self.CANCELED

        }
        status = data['cashout']['status']

        return Withdraw(
            tracking_id='',
            status=mapping_status.get(int(status), self.PENDING)
        )

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


class ZibalChannel(FiatWithdraw):

    def collect_api(self, path: str, method: str = 'GET', data: dict = None, timeout: float = 30) -> dict:

        url = 'https://api.zibal.ir' + path

        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': self.gateway.withdraw_api_secret},
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
        paya_banks = []

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

    def get_withdraw_status(self, request_id: int, provider_id: str) -> Withdraw:
        data = self.collect_api(f'/v1/report/checkout/inquire', method='POST', data={
            "walletId": self.gateway.wallet_id,
            'uniqueCode': str(request_id)
        })

        if 'details' in data:
            details = data['details'][0]
        else:
            details = {}

        if data['type'] == 'canceledCheckout':
            status = self.CANCELED
        elif data['type'] == 'checkoutQueue':
            status = self.PENDING
        else:
            mapping_status = {
                0: self.DONE,
                1: self.CANCELED,
                2: self.CANCELED,
            }
            status = details.get('checkoutStatus', self.PENDING)
            status = mapping_status.get(int(status), self.PENDING)

        return Withdraw(
            tracking_id=details.get('refCode'),
            status=status
        )

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

    def get_transactions(self, merchant_id: str, status: int):
        return self.collect_api(
            path='/v1/gateway/report/transaction',
            method='POST',
            data={'merchantId': merchant_id, 'status': status},
            timeout=45
        )

    def update_missing_payments(self, gateway: Gateway):
        transactions = self.get_transactions(gateway.merchant_id, status=2)

        for t in transactions:
            authority = t['trackId']

            payment_request = PaymentRequest.objects.get(authority=authority)
            payment = payment_request.get_or_create_payment()

            payment_request.get_gateway().verify(payment)


class ZarinpalChannel(FiatWithdraw):

    def get_total_wallet_irt_value(self):
        return 0


class JibitChannel(FiatWithdraw):
    BASE_URL = ' https://napi.jibit.ir/trf'
    INSTANT_BANKS = ['MELLI', 'RESALAT', 'KESHAVARZI', 'SADERAT', 'EGHTESAD_NOVIN', 'SHAHR', 'SEPAH',
                     'AYANDEH', 'SAMAN', 'TEJARAT', 'PARSIAN']

    def _get_token(self):
        resp = requests.post(
            url=self.BASE_URL + '/v2/tokens/generate',
            json={
                'apiKey': self.gateway.withdraw_api_key,
                'secretKey': self.gateway.withdraw_api_secret,
            },
            timeout=30,
        )

        if resp.ok:
            resp_data = resp.json()
            return resp_data['accessToken']

    def collect_api(self, path: str, method: str = 'GET', data: dict = None, timeout: float = 30) -> Response:
        url = 'https://napi.jibit.ir/trf' + path
        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': 'Bearer ' + self._get_token()},
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

        if self.verbose or not resp.ok:
            print('status', resp.status_code)
            print('data', resp_data)

        return Response(data=resp_data, success=resp.ok, status_code=resp.status_code)

    def get_wallet_data(self, wallet_id: int = None) -> Wallet:
        resp = self.collect_api('/v2/balances')
        balance = 0
        free = 0

        for d in resp.get_success_data()['balances']:
            balance_type = d['balanceType']

            if balance_type == 'STL':
                free = d['amount']

            if balance_type in ('STL', 'WLT'):
                balance += d['amount']

        return Wallet(
            id=0,
            name='main',
            balance=balance // 10,
            free=free // 10
        )

    def create_withdraw(self, wallet_id: int, receiver: BankAccount, amount: int, request_id) -> Withdraw:

        if receiver.bank in self.INSTANT_BANKS:
            transfer_mode = 'NORMAL'
        else:
            transfer_mode = 'ACH'

        resp = self.collect_api('/v2/transfers', method='POST', data={
            'submissionMode': 'TRANSFER',
            'batchID': 'wr-%s' % request_id,
            'transfers': [{
                'transferID': str(request_id),
                'destination': receiver.iban,
                'destinationFirstName': receiver.user.first_name,
                'destinationLastName': receiver.user.last_name,
                'amount': amount,
                'currency': 'TOMAN',
                'cancellable': False,
                'transferMode': transfer_mode,
                'description': 'برداشت کاربر'
            }],
        })

        if not resp.success:
            if resp.data['errors'][0]['code'] == 'transfer.already_exists':
                return Withdraw(
                    tracking_id='',
                    status=FiatWithdrawRequest.PENDING,
                )

            else:
                raise ServerError

        return Withdraw(
            tracking_id='',
            status=FiatWithdrawRequest.PENDING,
            receive_datetime=next_ach_clear_time()
        )

    def get_withdraw_status(self, request_id: int, provider_id: str) -> Withdraw:
        resp = self.collect_api('/v2/transfers?transferID={}'.format(request_id))
        data = resp.get_success_data()

        mapping_status = {
            'CANCELLED': self.CANCELED,
            'TRANSFERRED': self.DONE,
            'CANCELLING': self.CANCELED,
            'FAILED': self.CANCELED,
            'IN_PROGRESS': self.PENDING
        }

        transfer = data['transfers'][0]

        channel_status = transfer['state']
        tracking_id = transfer['bankTransferID'] or ''

        return Withdraw(
            tracking_id=tracking_id,
            status=mapping_status.get(channel_status, self.PENDING),
        )

    def get_estimated_receive_time(self, created: datetime):
        request_date = created.astimezone()
        receive_time = request_date.replace(microsecond=0)

        receive_time += timedelta(hours=3)

        return receive_time

    def get_total_wallet_irt_value(self) -> int:
        wallet = self.get_wallet_data()
        return wallet.balance


class JibimoChannel(FiatWithdraw):

    def _get_token(self):
        resp = requests.post('https://api.jibimo.com/v2/auth/token', headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }, json={
            'username': self.gateway.withdraw_api_key,
            'password': self.gateway.withdraw_api_password,
            'secret_key': self.gateway.withdraw_api_secret,
            'scopes': ['registered-user']
        })

        if resp.ok:
            resp = resp.json()
            return resp['token_type'] + ' ' + resp['access_token']

    def collect_api(self, path: str, method: str = 'GET', data: dict = None, timeout: float = 30) -> Response:
        url = 'https://api.jibimo.com' + path

        request_kwargs = {
            'url': url,
            'timeout': timeout,
            'headers': {'Authorization': self._get_token()},
        }

        try:
            if method == 'GET':
                resp = requests.get(params=data, **request_kwargs)
            else:
                method_prop = getattr(requests, method.lower())
                resp = method_prop(json=data, **request_kwargs)
        except requests.exceptions.ConnectionError:
            logger.error('jibimo connection error', extra={
                'url': url,
                'method': method,
                'data': data,
            })
            raise TimeoutError

        resp_data = resp.json()

        if self.verbose or not resp.ok:
            print('status', resp.status_code)
            print('data', resp_data)

        return Response(data=resp_data, success=resp.ok, status_code=resp.status_code)

    def get_total_wallet_irt_value(self) -> int:
        resp = self.collect_api('/v2/business/refresh')
        user = resp.data['user']
        return int(float(user['balance']) - float(user['reserved']))
