import logging
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q

from accounts.models import Account
from ledger.exceptions import AbruptDecrease
from ledger.models import OTCRequest, Trx, Asset
from ledger.utils.fields import get_lock_field
from ledger.utils.price import SELL
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class TokenExpired(Exception):
    pass


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE = 'pending', 'canceled', 'done'

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE)],
        verbose_name='وضعیت'
    )

    lock = get_lock_field()

    def change_status(self, status: str):
        self.status = status
        self.save()

    def create_ledger(self):
        system = Account.system()
        user = self.otc_request.account

        from_asset = self.otc_request.from_asset
        to_asset = self.otc_request.to_asset

        with transaction.atomic():
            Trx.objects.bulk_create([
                Trx(
                    sender=from_asset.get_wallet(user, market=self.otc_request.market),
                    receiver=from_asset.get_wallet(system, market=self.otc_request.market),
                    amount=self.otc_request.from_amount,
                    group_id=self.group_id,
                    scope=Trx.TRADE
                ),
                Trx(
                    sender=to_asset.get_wallet(system, market=self.otc_request.market),
                    receiver=to_asset.get_wallet(user, market=self.otc_request.market),
                    amount=self.otc_request.to_amount,
                    group_id=self.group_id,
                    scope=Trx.TRADE
                ),
            ])

    @property
    def client_order_id(self):
        return 'otc-%s' % self.id

    @classmethod
    def execute_trade(cls, otc_request: OTCRequest) -> 'OTCTrade':

        if otc_request.expired():
            raise TokenExpired()

        account = otc_request.account

        from_asset = otc_request.from_asset
        conf = otc_request.get_trade_config()

        conf.coin.is_trade_amount_valid(conf.coin_amount, raise_exception=True)

        from_wallet = from_asset.get_wallet(account, market=otc_request.market)

        cls.check_abrupt_decrease(otc_request)

        lock = from_wallet.lock_balance(otc_request.from_amount)

        otc_trade = OTCTrade.objects.create(
            otc_request=otc_request,
            lock=lock
        )

        otc_trade.hedge_and_finalize()

        # if otc_request.account.user.first_trade_prize_activate:
        #     from ledger.models import Asset, Prize
        #     from ledger.models.prize import alert_user_prize
        #
        #     account = otc_request.account
        #     if OTCTrade.objects.filter(Q(otc_request__account__user_id=account.user)).count() == 1:
        #         with transaction.atomic():
        #             prize = Prize.objects.create(
        #                 account=account,
        #                 amount=Prize.FIRST_TRADE_PRIZE_AMOUNT,
        #                 scope=Prize.FIRST_TRADE_PRIZE,
        #                 asset=Asset.objects.get(symbol=Asset.SHIB),
        #             )
        #             prize.build_trx()
        #
        #         alert_user_prize(account.user, Prize.FIRST_TRADE_PRIZE)

        return otc_trade

    def hedge_and_finalize(self):
        conf = self.otc_request.get_trade_config()

        if self.otc_request.account.is_ordinary_user():
            hedged = ProviderOrder.try_hedge_for_new_order(
                asset=conf.coin,
                side=conf.side,
                amount=conf.coin_amount,
                scope=ProviderOrder.TRADE
            )
        else:
            hedged = True

        if hedged:
            with transaction.atomic():
                from market.models import FillOrder
                self.change_status(self.DONE)
                self.create_ledger()
                self.lock.release()
                FillOrder.create_for_otc_trade(self)

    @classmethod
    def check_abrupt_decrease(cls, otc_request: OTCRequest):
        old_coin_price = otc_request.to_price
        new_coin_price = otc_request.get_to_price()

        threshold = Decimal('0.0035')

        conf = otc_request.get_trade_config()

        if conf.side == SELL:
            old_coin_price = 1 / old_coin_price
            new_coin_price = 1 / new_coin_price

        if new_coin_price <= old_coin_price * (1 - threshold):
            logger.error('otc failed because of abrupt decrease!')
            raise AbruptDecrease()
