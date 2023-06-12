import json
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
            'callbackUrl': host_url + f'/api/v1/finance/paymentIds/callback/jibit/?id={user.id}',
            'merchantReferenceNumber': self.get_client_ref(user),
            'userFullName': user.get_full_name(),
            'userIbans': ibans,
            'userMobile': '09121234567',
        })

        if resp.success:
            destination = GeneralBankAccount.objects.get_or_create(
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
        
    def check_payment_id_status(self, payment_id: PaymentId):
        resp = self._collect_api(
            path=f'/v1/paymentIds/{self.get_client_ref(payment_id.user)}',
        )

        payment_id.verified = resp.data['registryStatus'] == 'VERIFIED'
        payment_id.save(update_fields=['verified'])

    def update_payment_ids(self, user: User):
        token = self._get_token()
        host_url = settings.HOST_URL

        resp = requests.put(
            url=self.BASE_URL + '/v1/paymentIds',
            headers={'Authorization': 'Bearer ' + token},
            params={
                'callbackUrl': host_url + f'/api/v1/finance/paymentIds/callback/jibit/?id={bank_account.id}',
                'merchantReferenceNumber': bank_account.id,
                'userFullName': bank_account.user.get_full_name(),
                'userIban': bank_account.iban,
                'userIbans': ibans,
            },
            timeout=30
        )
        if resp.ok:
            bank_payment_id.user_iban_list = json.dumps(resp.json()['userIbans'])
            bank_payment_id.save(update_fields=['user_iban_list'])

    def get_payments_id_transaction_status(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/paymentIds/u-{user.id}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )

        if resp.ok:
            payment_id_request.status = resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def get_waiting_payments_id_transaction_list(self, page_number=0, page_size=200):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/paymentIds/waitingForVerify/?pageNumber={page_number}&pageSize={page_size}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )

        if resp.ok:
            payments_list = resp.json().get('content', None)

            for payment in payments_list:
                PaymentIdRequest.objects.get_or_create(
                    external_reference_number=payment['externalReferenceNumber'],
                    defaults={
                        'bank_payment_id': BankPaymentId.objects.get(pay_id=payment['PaymentId']),
                        'payment_id': payment['PaymentId'],
                        'amount': payment['amount'],
                        'bank': payment['bank'],
                        'bank_reference_number': payment['bankReferenceNumber'],
                        'destination_account_identifier': payment['destinationAccountIdentifier'],
                        'raw_bank_timestamp': payment['rawBankTimestamp'],
                        'status': payment['status']
                    }
                )

    def verify_payments_id_transaction(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/{payment_id_request.external_reference_number}/verify/',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            payment_id_request.status = resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def fail_payments_id_transaction(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/{payment_id_request.external_reference_number}/fail',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            payment_id_request.status=resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def get_payments_id_payed_transaction_list(self, from_date, to_date, page_number=0, page_size=200):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/list/?pageNumber={page_number}&pageSize={page_size}&fromDate={from_date}'
                                f'&toDate={to_date}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            return resp.json()
