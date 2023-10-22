import logging
from datetime import timedelta
from decimal import Decimal
from json import JSONDecodeError

import jdatetime
import requests
from django.conf import settings
from django.utils import timezone
from urllib3.exceptions import ReadTimeoutError

from accounts.models import User
from accounts.utils.admin import url_to_admin_list
from accounts.utils.telegram import send_system_message
from accounts.verifiers.jibit import Response
from financial.models import BankAccount, PaymentIdRequest, PaymentId, Gateway
from financial.models.bank import GeneralBankAccount
from financial.utils.bank import get_bank
from ledger.utils.fields import PROCESS, PENDING

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, gateway):
        self.gateway = gateway

    def create_payment_id(self, user: User) -> PaymentId:
        raise NotImplementedError

    def create_payment_request(self, external_ref: str) -> PaymentIdRequest:
        raise NotImplementedError

    def verify_payment_request(self, payment_request: PaymentIdRequest):
        raise NotImplementedError

    def create_missing_payment_requests(self):
        pass

    def create_missing_payment_requests_from_list(self):
        pass

    def check_payment_id_status(self, payment_id: PaymentId):
        raise NotImplementedError


class JibitClient(BaseClient):
    BASE_URL = 'https://napi.jibit.cloud/pip'
    _token = None

    def _get_token(self, force_renew: bool = False):
        if not force_renew:
            if self._token:
                return self._token

        resp = requests.post(
            url=self.BASE_URL + '/v1/tokens/generate',
            json={
                'apiKey': self.gateway.payment_id_api_key,
                'secretKey': self.gateway.payment_id_secret,
            },
            timeout=30,
        )

        if resp.ok:
            resp_data = resp.json()
            self._token = resp_data['accessToken']
            return self._token

    def _collect_api(self, path: str, method: str = 'GET', data: dict = None) -> Response:
        if data is None:
            data = {}

        url = self.BASE_URL + path

        token = self._get_token()

        if not token:
            return Response(None, False, status_code=0)

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
            raise TimeoutError

        try:
            resp_json = resp.json()
        except JSONDecodeError:
            resp_json = None

        if not resp.ok:
            logger.info(f'{url} {resp.status_code}: {resp_json}')

        return Response(data=resp_json, success=resp.ok, status_code=resp.status_code)
    
    @classmethod
    def get_client_ref(cls, user: User):
        return f'u-{user.id}'

    def create_payment_id(self, user: User) -> PaymentId:
        existing = PaymentId.objects.filter(user=user, gateway=self.gateway).first()
        if existing:
            return existing

        host_url = settings.HOST_URL

        ibans = list(BankAccount.objects.filter(user=user, verified=True).values_list('iban', flat=True))

        resp = self._collect_api('/v1/paymentIds', method='POST', data={
            'callbackUrl': host_url + f'/api/v1/finance/paymentId/callback/jibit/',
            'merchantReferenceNumber': self.get_client_ref(user),
            'userFullName': user.get_full_name(),
            'userIbans': ibans,
            'userMobile': user.phone,
        })

        if resp.status_code == 400:
            resp = self.get_pay_id_data(user)

        assert resp.success

        destination, _ = GeneralBankAccount.objects.get_or_create(
            iban=resp.data['destinationIban'],
            defaults={
                'name': resp.data['destinationOwnerName'],
                'deposit_address': resp.data['destinationDepositNumber'],
                'bank': get_bank(swift_code=resp.data['destinationBank']).slug,
            }
        )

        payment_id = PaymentId.objects.create(
            user=user,
            gateway=self.gateway,
            pay_id=resp.data['payId'],
            verified=resp.data['registryStatus'] == 'VERIFIED',
            destination=destination
        )

        if not payment_id.verified:
            self.check_payment_id_status(payment_id)

        return payment_id

    def update_payment_id(self, payment_id: PaymentId):
        raise NotImplementedError

    def get_pay_id_data(self, user: User) -> Response:
        return self._collect_api(
            path=f'/v1/paymentIds/{self.get_client_ref(user)}',
        )

    def check_payment_id_status(self, payment_id: PaymentId):
        resp = self.get_pay_id_data(payment_id.user)

        payment_id.verified = resp.data['registryStatus'] == 'VERIFIED'
        payment_id.save(update_fields=['verified'])

    def _create_and_verify_payment_data(self, data: dict):
        merchant_ref = data['merchantReferenceNumber']
        user_id = int(merchant_ref[2:])
        payment_id = PaymentId.objects.get(pay_id=data['paymentId'], user_id=user_id)
        deposit_time = jdatetime.datetime.strptime(data['rawBankTimestamp'], '%Y/%m/%d %H:%M:%S').togregorian().astimezone()

        if data['status'] == 'SUCCESSFUL':
            status = PENDING
        else:
            status = PROCESS

        amount = data['amount'] // 10
        fee = amount * Decimal('0.0001')

        payment_request, created = PaymentIdRequest.objects.get_or_create(
            external_ref=data['externalReferenceNumber'],
            defaults={
                'bank_ref': data['bankReferenceNumber'],
                'amount': amount - fee,
                'fee': fee,
                'status': status,
                'owner': payment_id,
                'source_iban': data['sourceIdentifier'],
                'deposit_time': deposit_time,
            }
        )

        if not created and payment_request.status == PENDING:
            return

        if data['status'] == 'WAITING_FOR_MERCHANT_VERIFY':
            self.verify_payment_request(payment_request)

        if payment_request.status == PENDING:
            send_system_message("New payment id request", link=url_to_admin_list(payment_request))

        return payment_request

    def create_payment_request(self, external_ref: str) -> PaymentIdRequest:
        resp = self._collect_api(f'/v1/paymentIds/{external_ref}')
        return self._create_and_verify_payment_data(resp.data)

    def verify_payment_request(self, payment_request: PaymentIdRequest):
        if payment_request.status != PROCESS:
            return

        resp = self._collect_api(f'/v1/payments/{payment_request.external_ref}/verify')

        if resp.success:
            payment_request.status = PENDING
            payment_request.save(update_fields=['status'])

    def create_missing_payment_requests(self):
        resp = self._collect_api(f'/v1/payments/waitingForVerify?pageNumber=0&pageSize=100')

        for data in resp.get_success_data()['content']:
            self._create_and_verify_payment_data(data)

    def create_missing_payment_requests_from_list(self):
        now = timezone.now().astimezone().date() + timedelta(days=1)
        resp = self._collect_api(f'/v1/payments/list?fromDate={now - timedelta(days=7)}&toDate={now}')

        for data in resp.get_success_data()['content']:
            self._create_and_verify_payment_data(data)


class MockClient(BaseClient):
    def create_payment_id(self, user: User) -> PaymentId:
        gateway = Gateway.get_active_pay_id_deposit()

        destination, _ = GeneralBankAccount.objects.get_or_create(
            iban='IR760120020000008992439961',
            defaults={
                'name': 'ایوان رایان پیام',
                'bank': 'MELLAT',
                'deposit_address': '8992439961'
            }
        )

        pay_id, _ = PaymentId.objects.get_or_create(
            gateway=gateway,
            user=user,
            defaults={
                'pay_id': f'1111100000{user.id}',
                'destination': destination
            }
        )

        return pay_id

    def check_payment_id_status(self, payment_id: PaymentId):
        payment_id.verified = True
        payment_id.save(update_fields=['verified'])


def get_payment_id_client(gateway: Gateway) -> BaseClient:
    if settings.DEBUG_OR_TESTING_OR_STAGING:
        return MockClient(gateway)

    assert gateway.type == Gateway.JIBIT

    return JibitClient(gateway)
