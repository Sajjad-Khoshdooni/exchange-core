import logging
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.db.models import F

from accounts.gamification.gamify import check_prize_achievements
from ledger.models import Trx, OTCTrade, Asset
from ledger.models.trx import FakeTrx
from ledger.utils.fields import get_amount_field, get_group_id_field, get_price_field
from ledger.utils.precision import floor_precision, precision_to_step
from ledger.utils.price import get_tether_irt_price, BUY
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


@dataclass
class FillOrderTrxs:
    base: Trx
    trade: Trx
    taker_fee: Trx
    maker_fee: Trx


class Trade(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trades')
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)

    side = models.CharField(max_length=8, choices=Order.ORDER_CHOICES)

    amount = get_amount_field()
    price = get_price_field()
    is_maker = models.BooleanField()

    group_id = get_group_id_field()

    base_amount = get_amount_field()  # = amount * price
    fee_amount = get_amount_field()

    irt_value = models.PositiveIntegerField()
    OTC = 'otc'
    SYSTEM = 'system'
    MARKET = 'market'
    SOURCE_CHOICES = ((OTC, 'otc'), (MARKET, 'market'), (SYSTEM, 'system'))

    trade_source = models.CharField(
        max_length=8,
        choices=SOURCE_CHOICES,
        db_index=True,
        default=MARKET
    )

    TradesPair = namedtuple("TradesPair", "maker taker")

    class Meta:
        indexes = [
            models.Index(fields=['account', 'symbol']),
            models.Index(fields=['symbol', 'side', 'created']),
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.taker_order = None

    def __str__(self):
        return f'{self.symbol}-{self.side} ' \
               f'({self.order_id}) ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    def set_amounts(self, trade_trxs: FillOrderTrxs):
        self.base_amount = trade_trxs.base.amount
        self.fee_amount = trade_trxs.maker_fee.amount if self.is_maker else trade_trxs.taker_fee.amount

    def create_trade_trxs(self, ignore_fee=False, fake_trade: bool = False) -> FillOrderTrxs:
        trade_trx = self._create_trade_trx()
        base_trx = self._create_base_trx()

        if fake_trade:
            trade_trx = FakeTrx.from_trx(trade_trx)
            base_trx = FakeTrx.from_trx(base_trx)

        # make sure sender and receiver wallets have same market
        assert trade_trx.sender.market == base_trx.receiver.market
        assert trade_trx.receiver.market == base_trx.sender.market

        taker_fee = self._create_fee_trx(self.taker_order, is_taker=True)
        maker_fee = self._create_fee_trx(self.order, is_taker=False)

        if ignore_fee:
            taker_fee = FakeTrx.from_trx(taker_fee)
            maker_fee = FakeTrx.from_trx(maker_fee)

        return FillOrderTrxs(
            trade=trade_trx,
            base=base_trx,
            taker_fee=taker_fee,
            maker_fee=maker_fee
        )

    def init_referrals(self, trade_trxs: FillOrderTrxs):
        tether_irt = Decimal(1) if self.symbol.base_asset.symbol == self.symbol.base_asset.IRT else \
            get_tether_irt_price(BUY)

        from market.models import ReferralTrx
        referrals = ReferralTrx.get_trade_referrals(
            trade_trxs.maker_fee,
            trade_trxs.taker_fee,
            self.price,
            tether_irt,
            is_buyer_maker=self.side == Order.BUY,
        )
        ReferralTrxTuple = namedtuple("ReferralTrx", "referral trx")
        return ReferralTrxTuple(referrals, ReferralTrx.get_trx_list(referrals))

    def _create_trade_trx(self) -> Trx:
        return Trx.transaction(
            sender=self.order.wallet if self.taker_order.side == Order.BUY else self.taker_order.wallet,
            receiver=self.taker_order.wallet if self.taker_order.side == Order.BUY else self.order.wallet,
            amount=self.amount,
            group_id=self.group_id,
            scope=Trx.TRADE
        )

    def _create_base_trx(self) -> Trx:
        return Trx.transaction(
            sender=self.order.base_wallet if self.taker_order.side == Order.SELL else self.taker_order.base_wallet,
            receiver=self.taker_order.base_wallet if self.taker_order.side == Order.SELL else self.order.base_wallet,
            amount=self.amount * self.price,
            group_id=self.group_id,
            scope=Trx.TRADE
        )

    def _create_fee_trx(self, order: Order, is_taker: bool) -> Trx:
        fee = order.symbol.taker_fee if is_taker else order.symbol.maker_fee

        fee_wallet = order.wallet if order.side == Order.BUY else order.base_wallet
        trx_amount = fee * (self.amount if order.side == Order.BUY else self.amount * self.price)

        if trx_amount:
            referral = self.taker_order.wallet.account.referred_by if is_taker else \
                self.order.wallet.account.referred_by
            if referral:
                from market.models import ReferralTrx
                trx_amount *= Decimal(1) - (Decimal(ReferralTrx.REFERRAL_MAX_RETURN_PERCENT) / 100 - Decimal(
                    referral.owner_share_percent) / 100)

        return Trx.transaction(
            sender=fee_wallet,
            receiver=fee_wallet.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_wallet.market),
            amount=trx_amount,
            group_id=self.group_id,
            scope=Trx.COMMISSION
        )

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
                "from market_fillorder where symbol_id = %s and side = 'buy' and created between %s and %s group by tf order by tf",
                [interval_in_secs, interval_in_secs, symbol_id, start, end]
            )
        ]

    @classmethod
    def create_for_otc_trade(cls, otc_trade: 'OTCTrade'):
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
        trade_trxs = trades_pair.maker.create_trade_trxs()
        for trade in trades_pair:
            trade.set_amounts(trade_trxs)
        from market.models import ReferralTrx
        referral_trx = trades_pair.maker.init_referrals(trade_trxs)
        ReferralTrx.objects.bulk_create(list(filter(bool, referral_trx.referral)))
        Trx.objects.bulk_create(list(filter(lambda trx: trx and trx.amount, referral_trx.trx)))
        for trade in trades_pair:
            trade.save()

        # updating trade_volume_irt of accounts
        accounts = [trades_pair.maker.account, trades_pair.taker.account]

        for account in accounts:
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trades_pair.maker.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                check_prize_achievements(account)

        trade_trxs.taker_fee.save()
        trade_trxs.maker_fee.save()

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
        maker_trade.taker_order = taker_order
        return cls.TradesPair(
            maker=maker_trade,
            taker=cls(
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
        )
