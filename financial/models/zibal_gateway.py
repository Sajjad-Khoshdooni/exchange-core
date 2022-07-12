import requests
from django.conf import settings
from django.urls import reverse

from financial.models import Gateway, BankCard, PaymentRequest, Payment
from financial.models.gateway import GatewayFailed
from ledger.utils.fields import DONE, CANCELED
from ledger.utils.wallet_pipeline import WalletPipeline


class ZibalGateway(Gateway):
    BASE_URL = 'https://gateway.zibal.ir'

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        resp = requests.post(
            self.BASE_URL + '/v1/request',
            json={
                'merchant': self.merchant_id,
                'amount': amount * 10,
                'callbackUrl': settings.HOST_URL + reverse('finance:zibal-callback'),
                'description': 'افزایش اعتبار',
                'allowedCards': bank_card.card_pan
            }
        )

        if resp.json()['result'] != 100:
            raise GatewayFailed

        authority = resp.json()['trackId']

        return PaymentRequest.objects.create(
            bank_card=bank_card,
            amount=amount,
            gateway=self,
            authority=authority
        )

    def get_redirect_url(self, payment_request: PaymentRequest):
        return 'https://gateway.zibal.ir/start/{}'.format(payment_request.authority)

    def verify(self, payment: Payment):
        payment_request = payment.payment_request

        resp = requests.post(
            self.BASE_URL + '/v1/verify',
            json={
                'merchant': payment_request.gateway.merchant_id,
                'trackId': int(payment_request.authority)
            }
        )

        data = resp.json()

        if data['result'] == 100:
            with WalletPipeline() as pipeline:
                payment.status = DONE
                payment.ref_id = data.get('refNumber')
                payment.ref_status = data['status']
                payment.save()

                payment.accept(pipeline)

        else:
            payment.status = CANCELED
            payment.ref_status = data.get('status', '')
            payment.save()

    class Meta:
        proxy = True
