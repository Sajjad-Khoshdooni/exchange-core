import requests
from django.conf import settings
from django.core.cache import caches
from rest_framework.reverse import reverse
from yekta_config import secret
from yekta_config.config import config

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
                'apiKey': secret('JIBIT_PAYMENT_API_KEY'),
                'secretKey': secret('JIBIT_PAYMENT_SECRET_KEY'),
            },
            timeout=30,
            proxies={
                'https': config('IRAN_PROXY_IP', default='localhost') + ':3128',
                'http': config('IRAN_PROXY_IP', default='localhost') + ':3128',
                'ftp': config('IRAN_PROXY_IP', default='localhost') + ':3128',
            }
        )

        if resp.ok:
            resp_data = resp.json()
            token = resp_data['accessToken']
            expire = 23 * 3600
            token_cache.set(JIBIT_GATEWAY_ACCESS_KEY, token, expire)

            return token

    def create_payment_request(self, bank_card: BankCard, amount: int, source: str) -> PaymentRequest:
        token = self._get_token()

        payment_request = PaymentRequest.objects.create(
            bank_card=bank_card,
            amount=amount,
            gateway=self,
            source=source,
        )
        resp = requests.post(
            self.BASE_URL + '/v3/purchases',
            headers={'Authorization': 'Bearer' + token},
            json={
                'amount': amount * 10,
                'callbackUrl': settings.HOST_URL + reverse('finance:jibit-callback'),
                'clientReferenceNumber': str(payment_request.id),
                'currency': 'IRR',
                'description': 'افزایش اعتبار',
                'payerCardNumber': bank_card.card_pan
            }
        )

        if not resp.ok:
            raise GatewayFailed

        authority = resp.json()['purchaseId']
        payment_request.authority = authority
        payment_request.save(update_fields=['authority'])

        return payment_request

    @classmethod
    def get_payment_url(cls, authority: str):
        return 'https://napi.jibit.ir/ppg/v3/purchases/{}}/payments'.format(authority)

    def _verify(self, payment: Payment):
        payment_request = payment.payment_request
        token = self._get_token()
        resp = requests.post(
            headers={'Authorization': 'Bearer' + token},
            url=self.BASE_URL + '/v3/purchases/{purchaseId}/verify'.format(purchaseId=payment_request.authority),
        )

        status = resp.json()['status']

        if status == 'ALREADY_VERIFIED':
            logger.warning('duplicate verify!', extra={'payment_id': payment.id})

        if status in ('SUCCESSFUL', 'ALREADY_VERIFIED'):
            with WalletPipeline() as pipeline:
                payment.status = DONE
                payment.ref_status = status
                payment.save()

                payment.accept(pipeline)

        else:
            payment.status = CANCELED
            payment.ref_status = status
            payment.save()

    class Meta:
        proxy = True


