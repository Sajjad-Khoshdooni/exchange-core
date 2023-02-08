import logging
from uuid import uuid4

from decouple import config
from django.db import models
from django.db.models import F, Sum

from accounts.models import Account
from ledger.exceptions import HedgeError
from ledger.models import OTCRequest, Trx, Wallet
from ledger.utils.external_price import SELL
from ledger.utils.fields import get_amount_field
from ledger.utils.wallet_pipeline import WalletPipeline
from market.exceptions import NegativeGapRevenue
from market.models import Trade
from market.utils.order_utils import new_order
from market.utils.trade import register_fee_transactions

logger = logging.getLogger(__name__)


class TokenExpired(Exception):
    pass


OTC_ACCOUNT = config('OTC_ACCOUNT', cast=int)


class OTCTrade(models.Model):
    PENDING, CANCELED, DONE, REVERT = 'pending', 'canceled', 'done', 'revert'
    MARKET, PROVIDER = 'm', 'p'

    created = models.DateTimeField(auto_now_add=True)
    otc_request = models.OneToOneField('ledger.OTCRequest', on_delete=models.PROTECT)

    group_id = models.UUIDField(default=uuid4, db_index=True)

    status = models.CharField(
        default=PENDING,
        max_length=8,
        choices=[(PENDING, PENDING), (CANCELED, CANCELED), (DONE, DONE), (REVERT, REVERT)],
    )
    execution_type = models.CharField(max_length=1, choices=((MARKET, 'market'), (PROVIDER, 'provider')))

    gap_revenue = get_amount_field(default=0)
    order_id = models.PositiveIntegerField(null=True, blank=True)

    def change_status(self, status: str):
        self.status = status
        self.save(update_fields=['status'])

    def create_ledger(self, pipeline: WalletPipeline):
        user = self.otc_request.account

        from_asset = self.otc_request.from_asset
        to_asset = self.otc_request.to_asset

        pipeline.new_trx(
            sender=from_asset.get_wallet(user, market=self.otc_request.market),
            receiver=from_asset.get_wallet(OTC_ACCOUNT, market=self.otc_request.market),
            amount=self.otc_request.get_paying_amount(),
            group_id=self.group_id,
            scope=Trx.TRADE
        )
        pipeline.new_trx(
            sender=to_asset.get_wallet(OTC_ACCOUNT, market=self.otc_request.market),
            receiver=to_asset.get_wallet(user, market=self.otc_request.market),
            amount=self.otc_request.get_receiving_amount(),
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

        from_wallet = from_asset.get_wallet(account, market=otc_request.market)
        amount = otc_request.get_paying_amount()
        from_wallet.has_balance(amount, raise_exception=True)
        
        with WalletPipeline() as pipeline:
            otc_trade = OTCTrade.objects.create(
                otc_request=otc_request,
                execution_type=OTCTrade.MARKET,
            )
            
            fok_success = otc_trade.try_fok_fill(pipeline)
            
            if not fok_success:
                otc_trade.execution_type = OTCTrade.PROVIDER
                otc_trade.save(update_fields=['execution_type'])
                pipeline.new_lock(key=otc_trade.group_id, wallet=from_wallet, amount=amount, reason=WalletPipeline.TRADE)

        if not fok_success:
            otc_trade.try_provider_fill()

        return otc_trade

    def try_fok_fill(self, pipeline: WalletPipeline) -> bool:
        symbol = self.otc_request.symbol
        if symbol.enable:
            from market.models import Order

            fok_order = new_order(
                symbol=symbol,
                account=Account.objects.get(id=OTC_ACCOUNT),
                amount=self.otc_request.amount,
                price=self.otc_request.price,
                side=self.otc_request.side,
                time_in_force=Order.FOK
            )

            self.order_id = fok_order.id

            if fok_order.status == Order.FILLED:
                trades_net_rec = Trade.objects.filter(order_id=fok_order.id).aggregate(
                    net_rec=Sum(F('amount') * F('price') * F('base_usdt_price') - F('fee_usdt_value'))
                )['net_rec'] or 0

                self.gap_revenue = self.otc_request.get_net_receiving_value() - trades_net_rec
                if self.otc_request.side == SELL:
                    self.gap_revenue = -self.gap_revenue

                self.save(update_fields=['order_id', 'gap_revenue'])
                self.accept(pipeline)
                return True
            else:
                self.save(update_fields=['order_id'])

        return False

    def try_provider_fill(self):

        if self.otc_request.account.is_ordinary_user():
            try:
                self._hedge_with_provider()
            except (HedgeError, NegativeGapRevenue):
                logger.exception('Error in hedging otc request')
                self.cancel()
                raise

    def cancel(self,):
        with WalletPipeline() as pipeline:  # type: WalletPipeline
            pipeline.release_lock(self.group_id)
            self.change_status(self.CANCELED)

    def accept(self, pipeline: WalletPipeline):
        if self.execution_type == self.PROVIDER:
            pipeline.release_lock(self.group_id)

        self.change_status(self.DONE)
        self.create_ledger(pipeline)

        register_fee_transactions(
            pipeline=pipeline,
            trade=self.otc_request,
            wallet=self.otc_request.symbol.asset.get_wallet(self.otc_request.account),
            base_wallet=self.otc_request.symbol.base_asset.get_wallet(self.otc_request.account),
            group_id=self.group_id
        )

        # updating trade_volume_irt of accounts
        account = self.otc_request.account
        account.trade_volume_irt = F('trade_volume_irt') + self.otc_request.irt_value
        account.save(update_fields=['trade_volume_irt'])
        account.refresh_from_db()

        from gamify.utils import check_prize_achievements, Task
        check_prize_achievements(account, Task.TRADE)

    def _hedge_with_provider(self, hedge: bool = True):
        with WalletPipeline() as pipeline:  # type: WalletPipeline
            self.accept(pipeline)

            if hedge:
                req = self.otc_request

                from ledger.utils.provider import TRADE, get_provider_requester
                get_provider_requester().try_hedge_new_order(
                    request_id='otc:%s' % self.id,
                    asset=req.symbol.asset,
                    side=req.side,
                    amount=req.amount,
                    scope=TRADE
                )

    def revert(self):
        with WalletPipeline() as pipeline:
            self.status = self.REVERT
            self.save(update_fields=['status'])

            for trx in Trx.objects.filter(group_id=self.group_id):
                if trx.receiver.has_balance(trx.amount):
                    pipeline.new_trx(
                        sender=trx.receiver,
                        receiver=trx.sender,
                        amount=trx.amount,
                        group_id=trx.group_id,
                        scope=Trx.REVERT
                    )
                else:
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
