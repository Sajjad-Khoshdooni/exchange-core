import logging

from django.db import models

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

    @classmethod
    def get_active(cls) -> 'Gateway':
        gateway = Gateway.objects.filter(active=True).order_by('id').first()

        if gateway:
            return gateway.get_concrete_gateway()

    def get_concrete_gateway(self) -> 'Gateway':
        from financial.models import ZarinpalGateway, PaydotirGateway, ZibalGateway
        mapping = {
            self.ZARINPAL: ZarinpalGateway,
            self.PAYIR: PaydotirGateway,
            self.ZIBAL: ZibalGateway,
        }

        self.__class__ = mapping[self.type]

        return self

    def get_redirect_url(self, payment_request: PaymentRequest):
        raise NotImplementedError

    def create_payment_request(self, bank_card: BankCard, amount: int) -> PaymentRequest:
        raise NotImplementedError

    def verify(self, payment: Payment):
        raise NotImplementedError

    def __str__(self):
        return self.name


