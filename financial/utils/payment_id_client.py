import logging
from json import JSONDecodeError

import requests
from django.conf import settings
from urllib3.exceptions import ReadTimeoutError

from accounts.models import User
from accounts.verifiers.jibit import Response
from financial.models import BankAccount, PaymentIdRequest, PaymentId
from financial.models.bank import GeneralBankAccount
from financial.utils.bank import get_bank
from ledger.utils.fields import PROCESS, PENDING

logger = logging.getLogger(__name__)


class JibitClient:
    BASE_URL = 'https://napi.jibit.cloud/pip'

    def __init__(self, gateway):
        self.gateway = gateway
        self._token = None

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

        request_kwargs = {
            'url': url,
            'timeout': 30,
            'headers': {'Authorization': 'Bearer ' + self._get_token()},
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

        return Response(data=resp_json, success=resp.ok, status_code=resp.status_code)
    
    @classmethod
    def get_client_ref(cls, user: User):
        return f'u-{user.id}'

    def create_payment_id(self, user: User) -> PaymentId:
        existing = PaymentId.objects.filter(user=user, gateway=self.gateway).first()
        if existing:
            return existing

        host_url = settings.HOST_URL

        ibans = list(BankAccount.objects.filter(user=user).values_list('iban', flat=True))

        resp = self._collect_api('/v1/paymentIds', method='POST', data={
            'callbackUrl': host_url + f'/api/v1/finance/paymentId/callback/jibit/',
            'merchantReferenceNumber': self.get_client_ref(user),
            'userFullName': user.get_full_name(),
            'userIbans': ibans,
            'userMobile': '09121234567',
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

        return PaymentId.objects.create(
            user=user,
            gateway=self.gateway,
            pay_id=resp.data['payId'],
            verified=resp.data['registryStatus'] == 'VERIFIED',
            destination=destination
        )

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

    def create_payment_request(self, external_ref: str) -> PaymentIdRequest:
        resp = self._collect_api(f'/v1/paymentIds/{external_ref}')

        user_id = int(resp.data['merchantReferenceNumber'][2:])
        payment_id = PaymentId.objects.get(pay_id=resp.data['paymentId'], user_id=user_id)

        payment_request, _ = PaymentIdRequest.objects.get_or_create(
            external_ref=external_ref,

            defaults={
                'bank_ref': resp.data['bankReferenceNumber'],
                'amount': resp.data['amount'] // 10,
                'status': PROCESS,
                'payment_id': payment_id
            }
        )

        return payment_request

    def verify_payment_request(self, payment_request: PaymentIdRequest):
        if payment_request.status is not PROCESS:
            return

        resp = self._collect_api(f'/v1/paymentIds/{payment_request.external_ref}/verify')

        if resp.success:
            payment_request.status = PENDING
            payment_request.save(update_fields=['status'])

    def create_missing_payment_requests(self):
        resp = self._collect_api(f'/v1/paymentIds/waitingForVerify/?pageNumber=0&pageSize=200')

        for data in resp.get_success_data():
            payment_request = self.create_payment_request(data['externalReferenceNumber'])
            self.verify_payment_request(payment_request)
