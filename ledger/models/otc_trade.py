import logging
from decimal import Decimal
from uuid import uuid4

from django.db import models, IntegrityError

from accounts.models import Account
from ledger.exceptions import AbruptDecrease, HedgeError
from ledger.models import OTCRequest, Trx, Wallet
from ledger.utils.price import SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.exceptions import NegativeGapRevenue

logger = logging.getLogger(__name__)


class TokenExpired(Exception):
    pass


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE, REVERT = 'pending', 'canceled', 'done', 'revert'

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE), (REVERT, REVERT)],
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
    def execute_trade(cls, otc_request: OTCRequest, force: bool = False) -> 'OTCTrade':

        if otc_request.expired():
            raise TokenExpired()

        account = otc_request.account

        from_asset = otc_request.from_asset
        conf = otc_request.get_trade_config()

        if not force:
            conf.coin.is_trade_amount_valid(conf.coin_amount, raise_exception=True)

        from_wallet = from_asset.get_wallet(account, market=otc_request.market)
        amount = otc_request.from_amount
        from_wallet.has_balance(amount, raise_exception=True)

        if not force:
            cls.check_abrupt_decrease(otc_request)

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            otc_trade = OTCTrade.objects.create(
                otc_request=otc_request,
            )
            pipeline.new_lock(key=otc_trade.group_id, wallet=from_wallet, amount=amount, reason=WalletPipeline.TRADE)

        otc_trade.hedge_and_finalize()

        return otc_trade

    def hedge_and_finalize(self):

        if self.otc_request.account.is_ordinary_user():
            try:
                self.accept()
            except (HedgeError, NegativeGapRevenue):
                logger.exception('Error in hedging otc request')
                self.cancel()
                raise

    def cancel(self):
        with WalletPipeline() as pipeline:  # type: WalletPipeline
            pipeline.release_lock(self.group_id)
            self.change_status(self.CANCELED)

    def accept(self, hedge: bool = True):
        with WalletPipeline() as pipeline:  # type: WalletPipeline
            pipeline.release_lock(self.group_id)
            from market.models import Trade
            self.change_status(self.DONE)
            self.create_ledger(pipeline)
            Trade.create_for_otc_trade(self, pipeline)

            if hedge:
                conf = self.otc_request.get_trade_config()

                from ledger.utils.provider import TRADE, get_provider_requester
                get_provider_requester().try_hedge_new_order(
                    request_id='otc:%s' % self.id,
                    asset=conf.coin,
                    side=conf.side,
                    amount=conf.coin_amount,
                    scope=TRADE
                )

    @classmethod
    def check_abrupt_decrease(cls, otc_request: OTCRequest):
        return
        old_coin_price = otc_request.to_price
        new_coin_price = otc_request.get_to_price()

        rate = new_coin_price / old_coin_price - 1

        threshold = Decimal('0.002')

        conf = otc_request.get_trade_config()

        if conf.side == SELL:
            rate = -rate

        if rate > threshold:
            logger.error('otc failed because of abrupt change!')
            raise AbruptDecrease()

    def revert(self):
        with WalletPipeline() as pipeline:
            self.status = self.REVERT
            self.save(update_fields=['status'])

            for trx in Trx.objects.filter(group_id=self.group_id):
                try:
                    pipeline.new_trx(
                        sender=trx.receiver,
                        receiver=trx.sender,
                        amount=trx.amount,
                        group_id=trx.group_id,
                        scope=Trx.REVERT
                    )
                except IntegrityError:
                    pipeline.new_trx(
                        sender=trx.receiver.asset.get_wallet(trx.receiver.account, market=Wallet.DEBT),
                        receiver=trx.sender,
                        amount=trx.amount,
                        group_id=trx.group_id,
                        scope=Trx.REVERT
                    )

            from market.models import Trade
            Trade.objects.filter(group_id=self.group_id).update(status=Trade.REVERT)

    def __str__(self):
        return '%s [%s]' % (self.otc_request, self.status)
