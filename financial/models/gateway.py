import logging
from typing import Type

from django.db import models
from rest_framework.exceptions import ValidationError

from accounts.models import User, Notification
from financial.models import BankCard
from financial.models import PaymentRequest
from financial.models.payment import Payment
from ledger.exceptions import AbruptDecrease
from ledger.models import OTCRequest, Asset, Wallet, OTCTrade, FastBuyToken
from ledger.models.asset import InvalidAmount
from ledger.models.otc_trade import ProcessingError, TokenExpired
from ledger.utils.fields import DONE


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
    def get_active(cls, user: User = None) -> 'Gateway':
        if user and user.is_staff:
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

    def create_payment_request(self, bank_card: BankCard, amount: int, source : str) -> PaymentRequest:
        raise NotImplementedError

    def verify(self, payment: Payment):
        self._verify(payment=payment)
        fast_buy_token = FastBuyToken.objects.filter(payment_request=payment.payment_request).last()
        if fast_buy_token:
            self.create_otc_for_fast_buy_token(fast_buy_token=fast_buy_token, payment=payment)

    def create_otc_for_fast_buy_token(self, fast_buy_token: FastBuyToken, payment: Payment):

        fast_buy_token.status = FastBuyToken.DEPOSIT
        fast_buy_token.save(update_fields=['status'])
        if payment.status == DONE:
            otc_request = OTCRequest.new_trade(
                account=fast_buy_token.user.account,
                from_asset=Asset.get('IRT'),
                to_asset=fast_buy_token.asset,
                from_amount=fast_buy_token.amount,
                market=Wallet.SPOT,
            )
            fast_buy_token.otc_request = otc_request
            fast_buy_token.save(update_fields=['otc_request'])

            try:
                otc_trade = OTCTrade.execute_trade(otc_request)
                fast_buy_token.status = FastBuyToken.DONE
                fast_buy_token.save(update_fields=['status'])

                Notification.send(
                    recipient=fast_buy_token.user,
                    title='خرید رمز ارز.',
                    message='خرید {} تومان {} با موفقیت انجام شد.'.format(fast_buy_token.asset.symbol,
                                                                          fast_buy_token.amount),
                    level=Notification.SUCCESS
                )
                return otc_trade
            except :
                pass

    def _verify(self, payment: Payment):
        raise NotImplementedError

    def __str__(self):
        return self.name


