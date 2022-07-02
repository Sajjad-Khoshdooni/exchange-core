import logging
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.db.models import F, CheckConstraint, Q

from accounts.gamification.gamify import check_prize_achievements
from ledger.models import Trx, OTCTrade, Asset
from ledger.models.trx import FakeTrx
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.precision import floor_precision, precision_to_step
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

    hedge_price = get_amount_field(default=Decimal(0))
    gap_revenue = get_amount_field(default=Decimal(0))

    TradesPair = namedtuple("TradesPair", "maker taker")

    class Meta:
        indexes = [
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

    def create_trade_trxs(self, pipeline: WalletPipeline, taker_order: Order, ignore_fee=False, fake_trade: bool = False) -> FillOrderTrxs:
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
        fee = order.symbol.taker_fee if is_taker else order.symbol.maker_fee

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
    def get_last(cls, symbol: 'PairSymbol', max_datetime=None):
        qs = cls.objects.filter(symbol=symbol).exclude(trade_source=cls.OTC).order_by('-id')
        if max_datetime:
            qs = qs.filter(created__lte=max_datetime)
        return qs.first()

    def format_values(self):
        return {
            'amount': str(floor_precision(self.amount, self.symbol.step_size)),
            'price': str(floor_precision(self.price, self.symbol.tick_size)),
            'total': str(floor_precision(self.amount * self.price, self.symbol.tick_size)),
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
                "from market_trade where symbol_id = %s and side = 'buy' and created between %s and %s group by tf order by tf",
                [interval_in_secs, interval_in_secs, symbol_id, start, end]
            )
        ]

    @classmethod
    def create_for_otc_trade(cls, otc_trade: 'OTCTrade', pipeline: WalletPipeline):
        config = otc_trade.otc_request.get_trade_config()
        market_symbol = f'{config.coin.symbol}{config.cash.symbol}'.upper()
        symbol = PairSymbol.get_by(name=market_symbol)
        amount = floor_precision(config.coin_amount, symbol.step_size)
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
            status=Order.FILLED,
        )

        base_irt_price = 1

        if symbol.base_asset.symbol == Asset.USDT:
            try:
                base_irt_price = get_tether_irt_price(BUY)
            except:
                base_irt_price = 27000

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

        from market.models import ReferralTrx
        ReferralTrx.objects.bulk_create(list(filter(bool, referrals)))
        Trade.objects.bulk_create([*trades_pair])

        # updating trade_volume_irt of accounts
        accounts = [trades_pair.maker.account, trades_pair.taker.account]

        for account in accounts:
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trades_pair.maker.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                check_prize_achievements(account)

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

        maker_trade.set_gap_revenue()
        taker_trade.set_gap_revenue()

        maker_trade.taker_order = taker_order

        return cls.TradesPair(
            maker=maker_trade,
            taker=taker_trade,
        )

    def set_gap_revenue(self):
        self.gap_revenue = 0

        if self.trade_source == self.MARKET or self.order.wallet.account.is_system():
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
            gap_price = self.hedge_price - self.price
        else:
            gap_price = self.price - self.hedge_price

        self.gap_revenue = gap_price * self.amount

        if base_asset.symbol == Asset.USDT:
            self.gap_revenue *= get_tether_irt_price(side=reverse_side)
