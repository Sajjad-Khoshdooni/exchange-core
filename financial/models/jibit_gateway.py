import json

import requests
from django.conf import settings
from django.core.cache import caches
from django.db import transaction
from rest_framework.reverse import reverse
from decouple import config
from decouple import config

from financial.models import Gateway, BankCard, PaymentRequest, Payment, BankAccount, PaymentIdRequest, BankPaymentId
from financial.models.gateway import GatewayFailed, logger
from ledger.utils.fields import DONE, CANCELED
from ledger.utils.wallet_pipeline import WalletPipeline

token_cache = caches['token']
JIBIT_GATEWAY_ACCESS_KEY = 'jibit_gateway_key'


class JibitGateway(Gateway):
    BASE_URL = 'https://napi.jibit.cloud/ppg'

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

    def create_payment_request(self, bank_card: BankCard, amount: int, source: str) -> PaymentRequest:
        token = self._get_token()
        base_url = config('PAYMENT_PROXY_HOST_URL', default='') or settings.HOST_URL

        payment_request = PaymentRequest.objects.create(
            bank_card=bank_card,
            amount=amount,
            gateway=self,
            source=source,
        )
        resp = requests.post(
            self.BASE_URL + '/v3/purchases',
            headers={'Authorization': 'Bearer ' + token},
            json={
                'amount': amount * 10,
                'callbackUrl': base_url + reverse('finance:jibit-callback'),
                'clientReferenceNumber': str(payment_request.id),
                'currency': 'IRR',
                'description': 'افزایش اعتبار',
                'payerCardNumber': bank_card.card_pan
            },
            timeout=30,
        )

        if not resp.ok:
            print(resp.json())
            raise GatewayFailed

        authority = resp.json()['purchaseId']
        payment_request.authority = authority
        payment_request.save(update_fields=['authority'])

        return payment_request

    def get_initial_redirect_url(self, payment_request: PaymentRequest) -> str:
        payment_proxy = config('PAYMENT_PROXY_HOST_URL', default='')

        if not payment_proxy:
            return super().get_initial_redirect_url(payment_request)
        else:
            return payment_proxy + '/api/v1/finance/payment/go/?gateway={gateway}&authority={authority}'.format(
                gateway=self.JIBIT,
                authority=payment_request.authority
            )

    @classmethod
    def get_payment_url(cls, authority: str):
        return 'https://napi.jibit.cloud/ppg/v3/purchases/{}/payments'.format(authority)

    def _verify(self, payment: Payment):
        payment_request = payment.payment_request
        token = self._get_token()
        resp = requests.post(
            headers={'Authorization': 'Bearer ' + token},
            url=self.BASE_URL + '/v3/purchases/{purchaseId}/verify'.format(purchaseId=payment_request.authority),
            timeout=30,
        )

        status = resp.json()['status']

        if status == 'ALREADY_VERIFIED':
            logger.warning('duplicate verify!', extra={'payment_id': payment.id})

        if status in ('SUCCESSFUL', 'ALREADY_VERIFIED'):
            with WalletPipeline() as pipeline:
                payment.status = DONE
                payment.save(update_fields=['status', 'ref_status'])

                payment.accept(pipeline)

        else:
            payment.status = CANCELED
            payment.save(update_fields=['status', 'ref_status'])

    def create_payment_id(self, bank_account: BankAccount):
        token = self._get_token()
        base_url = config('PAYMENT_PROXY_HOST_URL', default='') or settings.HOST_URL

        resp = requests.post(
            url=self.BASE_URL + '/v1/paymentIds',
            headers={'Authorization': 'Bearer ' + token},
            params={
                "callbackUrl": base_url + f"paymentIds/callback/jibit/?id={bank_account.id}",
                "merchantReferenceNumber": bank_account.id,
                "userFullName": bank_account.user.name,
                "userIban": bank_account.iban,
                # "userIbans": [
                #     "string"
                # ],
                "userMobile": bank_account.user.phone,
            },
            timeout=30
        )
        if resp.ok:
            data = resp.json()
            BankPaymentId.objects.create(
                bank_account=bank_account,
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
        base_url = config('PAYMENT_PROXY_HOST_URL', default='') or settings.HOST_URL

        resp = requests.post(
            url=self.BASE_URL + '/v1/paymentIds',
            headers={'Authorization': 'Bearer ' + token},
            params={
                "callbackUrl": base_url + f"paymentIds/callback/jibit/?id={bank_account.id}",
                "merchantReferenceNumber": bank_account.id,
                "userFullName": bank_account.user.name,
                "userIban": bank_account.iban,
                "userIbans": ibans,
                "userMobile": bank_account.user.phone,
                # "userRedirectUrl": "string"
            },
            timeout=30
        )
        if resp.ok:
            bank_payment_id.user_iban_list = json.dumps(resp.json()['userIbans'])
            bank_payment_id.save(update_fields=['user_iban_list'])

    def get_payments_id_status(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/paymentIds/{payment_id_request.external_reference_number}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )

        if resp.ok:
            payment_id_request.status = resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def get_waiting_payments_id_list(self, page_number = 0, page_size = 200):
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
                    payment_id=payment['PaymentId'],
                    defaults={
                        "gateway": Gateway.objects.filter(type=Gateway.JIBIT).first(),
                        "amount": payment['amount'],
                        "bank": payment['bank'],
                        "bank_reference_number": payment['bankReferenceNumber'],
                        "destination_account_identifier": payment['destinationAccountIdentifier'],
                        "external_reference_number": payment['externalReferenceNumber'],
                        "raw_bank_timestamp": payment['rawBankTimestamp'],
                        "status": payment['status']
                    }
                )

    def verify_payments_id(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/{payment_id_request.external_reference_number}/verify/',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            payment_id_request.status = resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def fail_payments_id(self, payment_id_request: PaymentIdRequest):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/{payment_id_request.external_reference_number}/fail',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            payment_id_request.status=resp.json()['status']
            payment_id_request.save(update_fields=['status'])

    def get_payments_id_payed_list(self, from_date, to_date, page_number = 0, page_size = 200):
        token = self._get_token()

        resp = requests.get(
            url=self.BASE_URL + f'/v1/payments/list/?pageNumber={page_number}&pageSize={page_size}&fromDate={from_date}'
                                f'&toDate={to_date}',
            headers={'Authorization': 'Bearer ' + token},
            timeout=30
        )
        if resp.ok:
            return resp.json()

    class Meta:
        proxy = True
