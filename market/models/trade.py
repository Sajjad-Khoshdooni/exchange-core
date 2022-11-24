import logging
from collections import namedtuple, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from django.conf import settings
from django.db import models
from django.db.models import F, CheckConstraint, Q, Sum, Max, Min
from django.utils import timezone

from ledger.models import Trx, OTCTrade, Asset
from ledger.models.trx import FakeTrx
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.precision import floor_precision, precision_to_step, decimal_to_str
from ledger.utils.price import get_tether_irt_price, BUY, get_trading_price_irt, get_trading_price_usdt, SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


@dataclass
class FillOrderTrxs:
    base: FakeTrx
    trade: FakeTrx
    taker_fee: FakeTrx
    maker_fee: FakeTrx


class Trade(models.Model):
    OTC = 'otc'
    SYSTEM = 'system'
    SYSTEM_MAKER = 'sys-make'
    SYSTEM_TAKER = 'sys-take'
    MARKET = 'market'

    SOURCE_CHOICES = ((OTC, 'otc'), (MARKET, 'market'), (SYSTEM, 'system'), (SYSTEM_MAKER, SYSTEM_MAKER),
                      (SYSTEM_TAKER, SYSTEM_TAKER))

    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)

    side = models.CharField(max_length=8, choices=Order.ORDER_CHOICES)

    amount = get_amount_field()
    price = get_amount_field()
    is_maker = models.BooleanField()

    group_id = get_group_id_field()

    base_amount = get_amount_field()  # = amount * price
    fee_amount = get_amount_field()

    irt_value = models.PositiveIntegerField()

    trade_source = models.CharField(
        max_length=8,
        choices=SOURCE_CHOICES,
        db_index=True,
        default=MARKET
    )

    hedge_price = get_amount_field(null=True)
    gap_revenue = get_amount_field(null=True, default=Decimal(0))

    TradesPair = namedtuple("TradesPair", "maker taker")

    class Meta:
        indexes = [
            models.Index(fields=['created']),
            models.Index(fields=['account', 'symbol']),
            models.Index(fields=['symbol', 'side', 'created']),
        ]
        constraints = [
            CheckConstraint(check=Q(
                amount__gte=0,
                price__gte=0,
                base_amount__gte=0,
                fee_amount__gte=0,
            ), name='check_market_trade_amounts', ),
        ]

    def __str__(self):
        return f'{self.symbol}-{self.side} ' \
               f'({self.order_id}) ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    def set_amounts(self, trade_trxs: FillOrderTrxs):
        self.base_amount = trade_trxs.base.amount
        self.fee_amount = trade_trxs.maker_fee.amount if self.is_maker else trade_trxs.taker_fee.amount

    def create_trade_trxs(self, pipeline: WalletPipeline, taker_order: Order, ignore_fee=False,
                          fake_trade: bool = False) -> FillOrderTrxs:
        trade_trx = self._create_trade_trx(pipeline, taker_order, fake=fake_trade)
        base_trx = self._create_base_trx(pipeline, taker_order, fake=fake_trade)

        # make sure sender and receiver wallets have same market
        assert trade_trx.sender.market == base_trx.receiver.market
        assert trade_trx.receiver.market == base_trx.sender.market

        taker_fee = self._create_fee_trx(pipeline, taker_order, is_taker=True, fake=ignore_fee)
        maker_fee = self._create_fee_trx(pipeline, self.order, is_taker=False, fake=ignore_fee)

        return FillOrderTrxs(
            trade=trade_trx,
            base=base_trx,
            taker_fee=taker_fee,
            maker_fee=maker_fee
        )

    def create_referral(self, pipeline: WalletPipeline, fee_trx: FakeTrx, tether_irt: Decimal):
        from market.models import ReferralTrx
        return ReferralTrx.get_trade_referral(
            pipeline,
            fee_trx,
            self.price,
            tether_irt,
            sell=self.side == Order.SELL,
        )

    def _create_trade_trx(self, pipeline: WalletPipeline, taker_order: Order, fake: bool = False) -> FakeTrx:
        if self.side == Order.BUY:
            sender, receiver = taker_order.wallet, self.order.wallet
        else:
            sender, receiver = self.order.wallet, taker_order.wallet
        trx_data = {
            'sender': sender,
            'receiver': receiver,
            'amount': self.amount,
            'group_id': self.group_id,
            'scope': Trx.TRADE,
        }

        if not fake:
            pipeline.new_trx(**trx_data)

        return FakeTrx(**trx_data)

    def _create_base_trx(self, pipeline: WalletPipeline, taker_order: Order, fake: bool = False) -> FakeTrx:
        if self.side == Order.SELL:
            sender, receiver = taker_order.base_wallet, self.order.base_wallet
        else:
            sender, receiver = self.order.base_wallet, taker_order.base_wallet
        trx_data = {
            'sender': sender,
            'receiver': receiver,
            'amount': self.amount * self.price,
            'group_id': self.group_id,
            'scope': Trx.TRADE,
        }
        if not fake:
            pipeline.new_trx(**trx_data)

        return FakeTrx(**trx_data)

    def _create_fee_trx(self, pipeline: WalletPipeline, order: Order, is_taker: bool, fake: bool = False) -> FakeTrx:
        account = order.wallet.account
        fee = order.symbol.get_taker_fee(account) if is_taker else order.symbol.get_maker_fee(account)

        fee_wallet = order.wallet if order.side == Order.BUY else order.base_wallet
        trx_amount = fee * (self.amount if order.side == Order.BUY else self.amount * self.price)

        if trx_amount:
            referral = order.wallet.account.referred_by
            if referral:
                from market.models import ReferralTrx
                trx_amount *= Decimal(1) - (Decimal(ReferralTrx.REFERRAL_MAX_RETURN_PERCENT) / 100 - Decimal(
                    referral.owner_share_percent) / 100)

        trx_data = {
            'sender': fee_wallet,
            'receiver': fee_wallet.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_wallet.market),
            'amount': trx_amount,
            'group_id': self.group_id,
            'scope': Trx.COMMISSION,
        }

        if not fake:
            pipeline.new_trx(**trx_data)

        return FakeTrx(**trx_data)

    @classmethod
    def get_last(cls, symbol, max_datetime=None):
        qs = cls.objects.filter(symbol=symbol).exclude(trade_source=cls.OTC).order_by('-id')
        if max_datetime:
            qs = qs.filter(created__lte=max_datetime)
        return qs.first()

    def format_values(self):
        return {
            'amount': decimal_to_str(floor_precision(self.amount, self.symbol.step_size)),
            'price': decimal_to_str(floor_precision(self.price, self.symbol.tick_size)),
            'total': decimal_to_str(floor_precision(self.amount * self.price, self.symbol.tick_size)),
        }

    @classmethod
    def get_grouped_by_interval(cls, symbol_id: int, interval_in_secs: int, start: datetime, end: datetime):
        return [
            {'timestamp': group.tf, 'open': group.open[1], 'high': group.high, 'low': group.low,
             'close': group.close[1], 'volume': group.volume}
            for group in cls.objects.raw(
                "select min(id) as id, "
                "min(array[id, price]) as open, max(array[id, price]) as close, "
                "max(price) as high, min(price) as low, "
                "sum(amount) as volume, "
                "(date_trunc('seconds', (created - (timestamptz 'epoch' - interval '30 min')) / %s) * %s + (timestamptz 'epoch' - interval '30 min')) as tf "
                "from market_trade where symbol_id = %s and side = 'buy' and trade_source != 'otc' and created between %s and %s group by tf order by tf",
                [interval_in_secs, interval_in_secs, symbol_id, start, end]
            )
        ]

    @staticmethod
    def get_interval_top_prices(symbol_ids=None, min_datetime=None):
        min_datetime = min_datetime or (timezone.now() - timedelta(seconds=5))
        market_top_prices = defaultdict(lambda: Decimal())
        symbol_filter = {'symbol_id__in': symbol_ids} if symbol_ids else {}
        for depth in Trade.objects.filter(**symbol_filter, created__gte=min_datetime).values('symbol', 'side').annotate(
                max_price=Max('price'), min_price=Min('price')):
            market_top_prices[
                (depth['symbol'], depth['side'])
            ] = (depth['max_price'] if depth['side'] == Order.BUY else depth['min_price']) or Decimal()
        return market_top_prices

    @classmethod
    def create_for_otc_trade(cls, otc_trade: 'OTCTrade', pipeline: WalletPipeline):
        config = otc_trade.otc_request.get_trade_config()
        market_symbol = f'{config.coin.symbol}{config.cash.symbol}'.upper()
        symbol = PairSymbol.get_by(name=market_symbol)
        amount = config.coin_amount
        price = (config.cash_amount / config.coin_amount).quantize(
            precision_to_step(symbol.tick_size), rounding=ROUND_HALF_UP)
        system_wallet = symbol.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=otc_trade.otc_request.market)
        maker_order = Order.objects.create(
            wallet=system_wallet,
            symbol=symbol,
            amount=amount,
            price=price,
            side=Order.get_opposite_side(config.side),
            fill_type=Order.MARKET,
            filled_amount=amount,
            status=Order.FILLED,
        )
        taker_wallet = symbol.asset.get_wallet(otc_trade.otc_request.account, market=otc_trade.otc_request.market)
        taker_order = Order.objects.create(
            wallet=taker_wallet,
            symbol=symbol,
            amount=amount,
            price=price,
            side=config.side,
            fill_type=Order.MARKET,
            filled_amount=amount,
            status=Order.FILLED,
        )

        base_irt_price = 1

        if symbol.base_asset.symbol == Asset.USDT:
            base_irt_price = get_tether_irt_price(BUY)

        trades_pair = Trade.init_pair(
            symbol=symbol,
            taker_order=taker_order,
            maker_order=maker_order,
            amount=amount,
            price=price,
            irt_value=base_irt_price * price * amount,
            trade_source=Trade.OTC,
            group_id=otc_trade.group_id,
        )
        trade_trxs = trades_pair.maker.create_trade_trxs(pipeline, taker_order, fake_trade=True)

        tether_irt = Decimal(1) if symbol.base_asset.symbol == symbol.base_asset.IRT else \
            get_tether_irt_price(Order.BUY)
        referrals = []
        for trade in trades_pair:
            trade.set_amounts(trade_trxs)
            fee_trx = trade_trxs.maker_fee if trade.is_maker else trade_trxs.taker_fee
            referrals.append(trade.create_referral(pipeline, fee_trx, tether_irt))
            trade.set_gap_revenue()

        from market.models import ReferralTrx
        ReferralTrx.objects.bulk_create(list(filter(bool, referrals)))
        Trade.objects.bulk_create([*trades_pair])
        Trade.create_hedge_fiat_trxs([*trades_pair])

        # updating trade_volume_irt of accounts
        accounts = [trades_pair.maker.account, trades_pair.taker.account]

        for account in accounts:
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trades_pair.maker.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(account, Task.TRADE)

    @classmethod
    def init_pair(cls, symbol, taker_order, maker_order, amount, price, irt_value, trade_source, **kwargs):
        maker_trade = cls(
            symbol=symbol,
            order=maker_order,
            account=maker_order.wallet.account,
            side=maker_order.side,
            is_maker=True,
            trade_source=trade_source,
            amount=amount,
            price=price,
            irt_value=irt_value,
            **kwargs
        )

        taker_trade = cls(
            symbol=symbol,
            order=taker_order,
            account=taker_order.wallet.account,
            side=taker_order.side,
            is_maker=False,
            trade_source=trade_source,
            amount=amount,
            price=price,
            irt_value=irt_value,
            **kwargs
        )

        maker_trade.taker_order = taker_order

        return cls.TradesPair(
            maker=maker_trade,
            taker=taker_trade,
        )

    def get_fee_irt_value(self):
        if self.order.wallet.account.is_system():
            return 0

        if self.side == BUY:
            return self.irt_value * self.fee_amount / self.amount
        else:
            return self.irt_value * self.fee_amount / self.base_amount

    def set_gap_revenue(self):
        self.gap_revenue = 0

        fee = self.get_fee_irt_value()

        if self.trade_source == self.MARKET or self.order.wallet.account.is_system():
            self.gap_revenue = fee
            return

        reverse_side = BUY if self.side == SELL else SELL

        base_asset = self.order.symbol.base_asset

        if base_asset.symbol == Asset.IRT:
            get_price = get_trading_price_irt
        elif base_asset.symbol == Asset.USDT:
            get_price = get_trading_price_usdt
        else:
            raise NotImplementedError

        self.hedge_price = get_price(self.order.symbol.asset.symbol, side=reverse_side, raw_price=True)

        if self.side == BUY:
            gap_price = self.price - self.hedge_price
        else:
            gap_price = self.hedge_price - self.price

        self.gap_revenue = gap_price * self.amount

        if base_asset.symbol == Asset.USDT:
            self.gap_revenue *= get_tether_irt_price(side=reverse_side)

        self.gap_revenue += fee

    @staticmethod
    def get_account_orders_filled_price(account_id):
        return {
            trade['order_id']: (trade['sum_amount'], trade['sum_value']) for trade in
            Trade.objects.filter(account=account_id).annotate(
                value=F('amount') * F('price')
            ).values('order').annotate(sum_amount=Sum('amount'), sum_value=Sum('value')).values(
                'order_id', 'sum_amount', 'sum_value'
            )
        }

    @classmethod
    def get_top_prices(cls, symbol_id):
        from market.utils.redis import get_top_prices
        top_prices = get_top_prices(symbol_id, scope='stoploss')
        if not top_prices:
            top_prices = defaultdict(lambda: Decimal())
            for k, v in Trade.get_interval_top_prices([symbol_id]).items():
                top_prices[k[1]] = v
        return top_prices

    @classmethod
    def create_hedge_fiat_trxs(cls, trades: List['Trade']):
        from financial.models import FiatHedgeTrx
        trxs = []

        for trade in trades:
            if trade.order.symbol.base_asset.symbol == Asset.IRT and \
                    ((trade.is_maker and trade.trade_source == cls.SYSTEM_TAKER) or
                     (not trade.is_maker and trade.trade_source in [cls.OTC, cls.SYSTEM_MAKER])):

                hedge_price = get_trading_price_usdt(trade.order.symbol.asset.symbol, side=BUY, raw_price=True)

                usdt_price = get_tether_irt_price(BUY)
                usdt_amount = hedge_price * trade.amount
                irt_amount = usdt_amount * usdt_price

                if trade.side == BUY:
                    usdt_amount = -usdt_amount
                else:
                    irt_amount = -irt_amount

                trxs.append(FiatHedgeTrx(
                    base_amount=irt_amount,
                    target_amount=usdt_amount,
                    price=usdt_price,
                    source=FiatHedgeTrx.TRADE,
                    reason=str(trade.id)
                ))

        if trxs:
            FiatHedgeTrx.objects.bulk_create(trxs)
