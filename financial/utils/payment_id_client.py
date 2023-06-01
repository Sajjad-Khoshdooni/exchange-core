import json

import requests
from decouple import config
from django.conf import settings
from django.core.cache import caches

from financial.models import BankAccount, BankPaymentId, PaymentIdRequest, Gateway

token_cache = caches['token']
JIBIT_GATEWAY_ACCESS_KEY = 'jibit_gateway_key'


class Jibitclient():
    def __init__(self):
        self.BASE_URL = 'https://napi.jibit.cloud/ppg'

    def _get_token(self, force_renew: bool = False):
        if not force_renew:
            token = token_cache.get(JIBIT_GATEWAY_ACCESS_KEY)
            if token:
                return token

        resp = requests.post(
            url=self.BASE_URL + '/v3/tokens',
            json={
                'apiKey': config('JIBIT_PAYMENT_API_KEY'),
                'secretKey': config('JIBIT_PAYMENT_SECRET_KEY'),
            },
            timeout=30,
        )

        if resp.ok:
            resp_data = resp.json()
            token = resp_data['accessToken']
            expire = 23 * 3600
            token_cache.set(JIBIT_GATEWAY_ACCESS_KEY, token, expire)

            return token

    def create_payment_id(self, bank_account: BankAccount):
        token = self._get_token()
        host_url = settings.HOST_URL

        resp = requests.post(
            url=self.BASE_URL + '/v1/paymentIds',
            headers={'Authorization': 'Bearer ' + token},
            params={
                "callbackUrl": host_url + f"/api/v1/finance/paymentIds/callback/jibit/?id={bank_account.id}",
                "merchantReferenceNumber": bank_account.id,
                "userFullName": bank_account.user.get_full_name(),
                "userIban": bank_account.iban,
                "userIbans": [
                    bank_account.iban
                ],
            },
            timeout=30
        )
        if resp.ok:
            data = resp.json()
            BankPaymentId.objects.create(
                bank_account=bank_account,
                gateway=Gateway.objects.filter(type=Gateway.JIBIT).first(),
                destination_deposit_number=data['destinationDepositNumber'],
                destination_iban=data['destinationIban'],
                merchant_code=data['merchantCode'],
                merchant_name=data['merchantName'],
                merchant_reference_number=data['merchantReferenceNumber'],
                pay_id=data['payId'],
                registry_status=data['registryStatus'],
                user_iban=data['userIban']
            )

    def get_payment_id(self, bank_account: BankAccount):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/paymentIds/{bank_account.id}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )

        if resp.ok:
            return resp.json()

    def update_payment_ids(self, bank_payment_id: BankPaymentId, ibans):
        bank_account = bank_payment_id.bank_account
        token = self._get_token()
        host_url = settings.HOST_URL

        resp = requests.put(
            url=self.BASE_URL + '/v1/paymentIds',
            headers={'Authorization': 'Bearer ' + token},
            params={
                "callbackUrl": host_url + f"/api/v1/finance/paymentIds/callback/jibit/?id={bank_account.id}",
                "merchantReferenceNumber": bank_account.id,
                "userFullName": bank_account.user.get_full_name(),
                "userIban": bank_account.iban,
                "userIbans": ibans,
            },
            timeout=30
        )
        if resp.ok:
            bank_payment_id.user_iban_list = json.dumps(resp.json()['userIbans'])
            bank_payment_id.save(update_fields=['user_iban_list'])

    def get_payments_id_transaction_status(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/paymentIds/{payment_id_request.external_reference_number}',
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
                        "bank_payment_id": BankPaymentId.objects.get(pay_id=payment['PaymentId']),
                        "payment_id": payment['PaymentId'],
                        "amount": payment['amount'],
                        "bank": payment['bank'],
                        "bank_reference_number": payment['bankReferenceNumber'],
                        "destination_account_identifier": payment['destinationAccountIdentifier'],
                        "raw_bank_timestamp": payment['rawBankTimestamp'],
                        "status": payment['status']
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
