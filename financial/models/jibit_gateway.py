import requests
from django.conf import settings
from django.core.cache import caches
from rest_framework.reverse import reverse
from decouple import config
from decouple import config

from financial.models import Gateway, BankCard, PaymentRequest, Payment
from financial.models.gateway import GatewayFailed, logger
from ledger.utils.fields import DONE, CANCELED
from ledger.utils.wallet_pipeline import WalletPipeline

token_cache = caches['token']
JIBIT_GATEWAY_ACCESS_KEY = 'jibit_gateway_key'


class JibitGateway(Gateway):
    BASE_URL = 'https://napi.jibit.ir/ppg'

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
            }
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
        return 'https://napi.jibit.ir/ppg/v3/purchases/{}/payments'.format(authority)

    def _verify(self, payment: Payment):
        payment_request = payment.payment_request
        token = self._get_token()
        resp = requests.post(
            headers={'Authorization': 'Bearer ' + token},
            url=self.BASE_URL + '/v3/purchases/{purchaseId}/verify'.format(purchaseId=payment_request.authority),
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

    class Meta:
        proxy = True
