import logging
from typing import Type

from django.db import models

from accounts.models import User
from financial.models import BankCard
from financial.models import PaymentRequest
from financial.models.payment import Payment


logger = logging.getLogger(__name__)


class GatewayFailed(Exception):
    pass


class Gateway(models.Model):
    BASE_URL = None

    ZARINPAL = 'zarinpal'
    PAYIR = 'payir'
    ZIBAL = 'zibal'

    name = models.CharField(max_length=128)
    type = models.CharField(
        max_length=8,
        choices=((ZARINPAL, ZARINPAL), (PAYIR, PAYIR), (ZIBAL, ZIBAL))
    )
    merchant_id = models.CharField(max_length=128)
    active = models.BooleanField(default=False)
    active_for_staff = models.BooleanField(default=False)

    @classmethod
    def get_active(cls, user: User) -> 'Gateway':
        if user.is_staff:
            gateway = Gateway.objects.filter(active_for_staff=True).order_by('id').first()

            if gateway:
                return gateway.get_concrete_gateway()

        gateway = Gateway.objects.filter(active=True).order_by('id').first()

        if gateway:
            return gateway.get_concrete_gateway()

    @classmethod
    def get_gateway_class(cls, type: str) -> Type['Gateway']:
        from financial.models import ZarinpalGateway, PaydotirGateway, ZibalGateway
        mapping = {
            cls.ZARINPAL: ZarinpalGateway,
            cls.PAYIR: PaydotirGateway,
            cls.ZIBAL: ZibalGateway,
        }

        return mapping.get(type)

    def get_concrete_gateway(self) -> 'Gateway':
        self.__class__ = self.get_gateway_class(self.type)
        return self

    def get_initial_redirect_url(self, payment_request: PaymentRequest):
        return self.get_payment_url(payment_request.authority)

    @classmethod
    def get_payment_url(cls, authority: str):
        raise NotImplementedError

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        raise NotImplementedError

    def verify(self, payment: Payment):
        raise NotImplementedError

    def __str__(self):
        return self.name


