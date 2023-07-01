import logging
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F, Sum

from _base.settings import OTC_ACCOUNT_ID
from accounting.models import TradeRevenue
from accounts.models import Account
from ledger.exceptions import HedgeError
from ledger.models import OTCRequest, Trx, Wallet, Asset
from ledger.utils.external_price import SELL, BUY
from ledger.utils.fields import get_amount_field
from ledger.utils.precision import floor_precision
from ledger.utils.wallet_pipeline import WalletPipeline
from market.exceptions import NegativeGapRevenue
from market.models import Trade, PairSymbol
from market.utils.order_utils import new_order
from market.utils.trade import register_fee_transactions

logger = logging.getLogger(__name__)


class TokenExpired(Exception):
    pass


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
            receiver=from_asset.get_wallet(OTC_ACCOUNT_ID, market=self.otc_request.market),
            amount=self.otc_request.get_paying_amount(),
            group_id=self.group_id,
            scope=Trx.TRADE
        )
        pipeline.new_trx(
            sender=to_asset.get_wallet(OTC_ACCOUNT_ID, market=self.otc_request.market),
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
                pipeline.new_lock(key=otc_trade.group_id, wallet=from_wallet, amount=amount,
                                  reason=WalletPipeline.TRADE)

        if not fok_success:
            otc_trade.try_provider_fill()

        return otc_trade

    def try_fok_fill(self, pipeline: WalletPipeline) -> bool:
        assert self.execution_type == self.MARKET

        symbol = self.otc_request.symbol
        if symbol.enable:
            from market.models import Order

            fok_order = new_order(
                pipeline=pipeline,
                symbol=symbol,
                account=Account.objects.get(id=OTC_ACCOUNT_ID),
                amount=self.otc_request.amount,
                price=self.otc_request.price,
                side=self.otc_request.side,
                time_in_force=Order.FOK,
                pass_min_notional=True
            )

            self.order_id = fok_order.id

            if fok_order.status == Order.FILLED:
                trades_base_sum = Trade.objects.filter(order_id=fok_order.id).aggregate(
                    sum=Sum(F('amount') * F('price'))
                )['sum'] or 0
                if symbol.base_asset.symbol == Asset.USDT:
                    base_usdt_price = 1
                else:
                    opposite_side = Order.get_opposite_side(self.otc_request.side)
                    usdt_irt = PairSymbol.objects.get(name='USDTIRT')
                    usdt_hedge_price = Order.get_top_price(
                        usdt_irt.id, opposite_side
                    )
                    if usdt_hedge_price:
                        base_usdt_price = 1 / usdt_hedge_price
                        self.otc_request.base_usdt_price = base_usdt_price
                        self.otc_request.save(update_fields=['base_usdt_price'])
                    else:
                        base_usdt_price = self.otc_request.base_usdt_price

                otc_base_amount = self.otc_request.amount * self.otc_request.price
                self.gap_revenue = (otc_base_amount - trades_base_sum) * base_usdt_price
                if self.otc_request.side == SELL:
                    self.gap_revenue = -self.gap_revenue

                self.save(update_fields=['order_id', 'gap_revenue'])
                self.accept(pipeline)

                TradeRevenue.new(
                    user_trade=self.otc_request,
                    group_id=self.group_id,
                    source=TradeRevenue.OTC_MARKET,
                    hedge_key=str(fok_order.id),
                ).save()

                return True
            else:
                self.save(update_fields=['order_id'])

        return False

    def try_provider_fill(self):

        if self.otc_request.account.is_ordinary_user():
            try:
                self.hedge_with_provider()
            except (HedgeError, NegativeGapRevenue):
                logger.exception('Error in hedging otc request')
                self.cancel()
                raise

    def cancel(self, ):
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

    def hedge_with_provider(self, hedge: bool = True):
        assert self.execution_type == self.PROVIDER

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            self.accept(pipeline)
            hedge_key = ''

            if hedge:
                req = self.otc_request
                _key = 'otc:%s' % self.id

                from ledger.utils.provider import TRADE, get_provider_requester
                hedged = get_provider_requester().try_hedge_new_order(
                    request_id=_key,
                    asset=req.symbol.asset,
                    side=req.side,
                    amount=req.amount,
                    scope=TRADE
                )

                if settings.ZERO_USDT_HEDGE and req.symbol.name != 'USDTIRT' and req.symbol.base_asset.symbol == Asset.IRT:
                    from market.models import Order
                    usdt_irt = PairSymbol.objects.get(name='USDTIRT')

                    amount = floor_precision(req.usdt_value, usdt_irt.tick_size)

                    order = new_order(
                        pipeline=pipeline,
                        symbol=usdt_irt,
                        account=Account.objects.get(id=OTC_ACCOUNT_ID),
                        side=req.side,
                        amount=amount,
                        fill_type=Order.MARKET,
                        raise_exception=False
                    )
                    if order.trades:
                        filled_amount = sum(map(lambda t: t.amount, order.trades))
                        if filled_amount:
                            filled_value = sum(map(lambda t: t.amount * t.price, order.trades))
                            filled_price = filled_value / filled_amount
                            self.otc_request.base_usdt_price = 1 / filled_price

                if hedged:
                    hedge_key = _key

            from accounting.models.revenue import TradeRevenue
            TradeRevenue.new(
                user_trade=self.otc_request,
                group_id=self.group_id,
                source=TradeRevenue.OTC_PROVIDER,
                hedge_key=hedge_key,
            ).save()

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
