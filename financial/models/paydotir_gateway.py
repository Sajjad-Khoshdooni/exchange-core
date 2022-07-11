import requests
from django.conf import settings
from django.urls import reverse

from financial.models import Gateway, BankCard, PaymentRequest, Payment
from financial.models.gateway import GatewayFailed
from ledger.utils.fields import DONE, CANCELED
from ledger.utils.wallet_pipeline import WalletPipeline


class PaydotirGateway(Gateway):
    BASE_URL = 'https://pay.ir'

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        resp = requests.post(
            self.BASE_URL + '/pg/send',
            json={
                'api': self.merchant_id,
                'amount': amount * 10,
                'description': 'افزایش اعتبار',
                'redirect': settings.HOST_URL + reverse('finance:paydotir-callback'),
                'validCardNumber': bank_card.card_pan
            }
        )

        resp_data = resp.json()

        if not resp.ok or resp_data['status'] != 1:
            print('status code', resp.status_code)
            print('body', resp_data)

            raise GatewayFailed

        authority = resp.json()['token']

        return PaymentRequest.objects.create(
            bank_card=bank_card,
            amount=amount,
            gateway=self,
            authority=authority
        )

    def get_redirect_url(self, payment_request: PaymentRequest):
        return 'https://pay.ir/pg/{}'.format(payment_request.authority)

    def verify(self, payment: Payment):
        payment_request = payment.payment_request

        resp = requests.post(
            self.BASE_URL + '/pg/verify',
            data={
                'api': payment_request.gateway.merchant_id,
                'token': payment_request.authority
            }
        )

        data = resp.json()

        if data['status'] == 1:
            with WalletPipeline() as pipeline:
                payment.status = DONE
                payment.ref_id = data.get('transId')
                payment.ref_status = data['status']
                payment.save()

                payment.accept(pipeline)

        else:
            payment.status = CANCELED
            payment.ref_status = data['status']
            payment.save()

    class Meta:
        proxy = True
