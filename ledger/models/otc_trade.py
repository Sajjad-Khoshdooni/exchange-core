import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models

from accounts.models import Account
from ledger.exceptions import AbruptDecrease
from ledger.models import OTCRequest, Trx
from ledger.utils.price import SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class TokenExpired(Exception):
    pass


class ProcessingError(Exception):
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

    def change_status(self, status: str):
        self.status = status
        self.save()

    def create_ledger(self, pipeline: WalletPipeline):
        system = Account.system()
        user = self.otc_request.account

        from_asset = self.otc_request.from_asset
        to_asset = self.otc_request.to_asset

        pipeline.new_trx(
            sender=from_asset.get_wallet(user, market=self.otc_request.market),
            receiver=from_asset.get_wallet(system, market=self.otc_request.market),
            amount=self.otc_request.from_amount,
            group_id=self.group_id,
            scope=Trx.TRADE
        )
        pipeline.new_trx(
            sender=to_asset.get_wallet(system, market=self.otc_request.market),
            receiver=to_asset.get_wallet(user, market=self.otc_request.market),
            amount=self.otc_request.to_amount,
            group_id=self.group_id,
            scope=Trx.TRADE
        )

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
        amount = otc_request.from_amount
        from_wallet.has_balance(amount, raise_exception=True)

        cls.check_abrupt_decrease(otc_request)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            otc_trade = OTCTrade.objects.create(
                otc_request=otc_request,
            )
            pipeline.new_lock(key=otc_trade.group_id, wallet=from_wallet, amount=amount)

        otc_trade.hedge_and_finalize()

        return otc_trade

    def hedge_and_finalize(self):
        conf = self.otc_request.get_trade_config()

        if self.otc_request.account.is_ordinary_user():
            try:
                hedged = ProviderOrder.try_hedge_for_new_order(
                    asset=conf.coin,
                    side=conf.side,
                    amount=conf.coin_amount,
                    scope=ProviderOrder.TRADE
                )
            except:
                logger.exception('Error in hedging otc request')
                hedged = False
        else:
            hedged = True

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            pipeline.release_lock(self.group_id)

            if hedged:
                from market.models import FillOrder
                self.change_status(self.DONE)
                self.create_ledger(pipeline)
                FillOrder.create_for_otc_trade(self)
            else:
                self.change_status(self.CANCELED)

        if not hedged:
            raise ProcessingError

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
