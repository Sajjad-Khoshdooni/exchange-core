import logging

import requests
from django.conf import settings
from django.db import models, transaction
from django.shortcuts import redirect
from django.urls import reverse

from financial.models import BankCard
from financial.models import PaymentRequest
from financial.models.payment import Payment
from ledger.utils.fields import DONE, CANCELED

logger = logging.getLogger(__name__)


class GatewayFailed(Exception):
    pass


class Gateway(models.Model):
    BASE_URL = None

    ZARINPAL = 'zarinpal'
    PAYDOTIR = 'paydotir'

    name = models.CharField(max_length=128)
    type = models.CharField(
        max_length=8,
        choices=((ZARINPAL, ZARINPAL), (PAYDOTIR, PAYDOTIR))
    )
    merchant_id = models.CharField(max_length=128)
    active = models.BooleanField(default=False)

    @classmethod
    def get_active(cls) -> 'Gateway':
        gateway = Gateway.objects.filter(active=True).order_by('id').first()

        if gateway:
            return gateway.get_concrete_gateway()

    def get_concrete_gateway(self) -> 'Gateway':
        mapping = {
            self.ZARINPAL: ZarinpalGateway,
            self.PAYDOTIR: PaydotirGateway
        }

        self.__class__ = mapping[self.type]

        return self

    def get_redirect_url(self, payment_request: PaymentRequest):
        raise NotImplementedError

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        raise NotImplementedError

    def verify(self, payment: Payment):
        raise NotImplementedError


class ZarinpalGateway(Gateway):
    BASE_URL = 'https://api.zarinpal.com'

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        resp = requests.post(
            self.BASE_URL + '/pg/v4/payment/request.json',
            json={
                'merchant_id': self.merchant_id,
                'amount': amount,
                'currency': 'IRT',
                'description': 'افزایش اعتبار',
                'callback_url': settings.HOST_URL + reverse('finance:zarinpal-callback'),
                'metadata': {"card_pan":  bank_card.card_pan}
            }
        )

        if not resp.ok or resp.json()['data']['code'] != 100:
            raise GatewayFailed

        authority = resp.json()['data']['authority']

        return PaymentRequest.objects.create(
            bank_card=bank_card,
            amount=amount,
            gateway=self,
            authority=authority
        )

    def get_redirect_url(self, payment_request: PaymentRequest):
        return 'https://www.zarinpal.com/pg/StartPay/{}'.format(payment_request.authority)

    def verify(self, payment: Payment):
        payment_request = payment.payment_request

        resp = requests.post(
            self.BASE_URL + '/pg/v4/payment/verify.json',
            data={
                'merchant_id': payment_request.gateway.merchant_id,
                'amount': payment_request.amount,
                'authority': payment_request.authority
            }
        )

        data = resp.json()['data']

        if data['code'] == 101:
            logger.warning('duplicate verify!', extra={'payment_id': payment.id})

        if data['code'] in (100, 101):
            with transaction.atomic():
                payment.status = DONE
                payment.ref_id = data.get('ref_id')
                payment.ref_status = data['code']
                payment.save()

                payment.accept()

        else:
            payment.status = CANCELED
            payment.ref_status = data['code']
            payment.save()

    class Meta:
        proxy = True


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

        if not resp.ok or resp.json()['status'] != 1:
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
            self.BASE_URL + '/pg/verify ',
            data={
                'api': payment_request.gateway.merchant_id,
                'token': payment_request.authority
            }
        )

        data = resp.json()

        if data['status'] == 1:
            with transaction.atomic():
                payment.status = DONE
                payment.ref_id = data.get('transId')
                payment.ref_status = data['status']
                payment.save()

                payment.accept()

        else:
            payment.status = CANCELED
            payment.ref_status = data['status']
            payment.save()

    class Meta:
        proxy = True
