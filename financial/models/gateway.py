import logging
from typing import Type

from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import User
from financial.models import BankCard
from financial.models import PaymentRequest
from financial.models.payment import Payment
from financial.utils.encryption import decrypt
from ledger.models import FastBuyToken

logger = logging.getLogger(__name__)


class GatewayFailed(Exception):
    pass


class Gateway(models.Model):
    BASE_URL = None

    ZARINPAL = 'zarinpal'
    PAYIR = 'payir'
    ZIBAL = 'zibal'
    JIBIT = 'jibit'

    name = models.CharField(max_length=128)
    type = models.CharField(
        max_length=8,
        choices=((ZARINPAL, ZARINPAL), (PAYIR, PAYIR), (ZIBAL, ZIBAL), (JIBIT, JIBIT))
    )
    merchant_id = models.CharField(max_length=128, blank=True)

    withdraw_enable = models.BooleanField(default=False)
    active = models.BooleanField(default=False)
    active_for_staff = models.BooleanField(default=False)

    min_deposit_amount = models.PositiveIntegerField(default=10000)
    max_deposit_amount = models.PositiveIntegerField(default=50000000)

    max_auto_withdraw_amount = models.PositiveIntegerField(null=True, blank=True)
    expected_withdraw_datetime = models.DateTimeField(null=True, blank=True)

    withdraw_api_key = models.CharField(max_length=1024, blank=True)
    withdraw_api_secret_encrypted = models.CharField(max_length=4096, blank=True)

    deposit_api_key = models.CharField(max_length=1024, blank=True)
    deposit_api_secret_encrypted = models.CharField(max_length=4096, blank=True)

    wallet_id = models.PositiveIntegerField(null=True, blank=True)

    def clean(self):
        if not self.active and not Gateway.objects.filter(active=True).exclude(id=self.id):
            raise ValidationError('At least one gateway should be active')

    @property
    def withdraw_api_secret(self):
        return decrypt(self.withdraw_api_secret_encrypted)

    @property
    def deposit_api_secret(self):
        return decrypt(self.deposit_api_secret_encrypted)

    @classmethod
    def get_active_deposit(cls, user: User = None) -> 'Gateway':
        if user and user.is_staff:
            gateway = Gateway.objects.filter(active_for_staff=True).order_by('id').first()

            if gateway:
                return gateway.get_concrete_gateway()

        gateway = Gateway.objects.filter(active=True).order_by('id').first()

        if gateway:
            return gateway.get_concrete_gateway()

    @classmethod
    def get_active_withdraw(cls) -> 'Gateway':
        return Gateway.objects.filter(withdraw_enable=True).order_by('id').first()

    @classmethod
    def get_gateway_class(cls, type: str) -> Type['Gateway']:
        from financial.models import ZarinpalGateway, PaydotirGateway, ZibalGateway, JibitGateway
        mapping = {
            cls.ZARINPAL: ZarinpalGateway,
            cls.PAYIR: PaydotirGateway,
            cls.ZIBAL: ZibalGateway,
            cls.JIBIT: JibitGateway
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

    def create_payment_request(self, bank_card: BankCard, amount: int, source : str) -> PaymentRequest:
        raise NotImplementedError

    def verify(self, payment: Payment):
        self._verify(payment=payment)

        fast_buy_token = FastBuyToken.objects.filter(payment_request=payment.payment_request).last()

        if fast_buy_token:
            fast_buy_token.create_otc_for_fast_buy_token(payment)

    def _verify(self, payment: Payment):
        raise NotImplementedError

    def __str__(self):
        return '%s (%s)' % (self.name, self.id)
