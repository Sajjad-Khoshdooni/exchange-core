import logging
from collections import namedtuple
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.db.models import F

from accounts.gamification.gamify import check_prize_achievements
from accounts.models import Account
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


class FillOrder(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)

    taker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='taken_fills')
    maker_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='made_fills')

    amount = get_amount_field()
    price = get_price_field()
    is_buyer_maker = models.BooleanField()

    group_id = get_group_id_field()

    base_amount = get_amount_field()  # = amount * price
    taker_fee_amount = get_amount_field()
    maker_fee_amount = get_amount_field()

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

    def save(self, **kwargs):
        assert self.taker_order.symbol == self.maker_order.symbol == self.symbol
        super(FillOrder, self).save(**kwargs)

    class Meta:
        indexes = [
            models.Index(fields=['created', 'symbol', ]),
        ]

    def get_side(self, account: Account, list_index: int):
        # refactor to remove list_index
        buy_order = self.maker_order if self.is_buyer_maker else self.taker_order
        sell_order = self.taker_order if self.is_buyer_maker else self.maker_order
        if buy_order.wallet.account != sell_order.wallet.account:
            if account == buy_order.wallet.account:
                return Order.BUY
            if account == sell_order.wallet.account:
                return Order.SELL
            raise Exception('invalid account')
        else:
            return Order.BUY if list_index % 2 == 0 else Order.SELL

    def get_fee(self, account: Account, list_index: int):
        if self.is_buyer_maker:
            return self.maker_fee_amount if self.get_side(account, list_index) == Order.BUY else self.taker_fee_amount
        else:
            return self.maker_fee_amount if self.get_side(account, list_index) == Order.SELL else self.taker_fee_amount

    def set_amounts(self, trade_trxs: FillOrderTrxs):
        self.base_amount = trade_trxs.base.amount
        self.taker_fee_amount = trade_trxs.taker_fee.amount
        self.maker_fee_amount = trade_trxs.maker_fee.amount

    def __str__(self):
        return f'{self.symbol}-{Order.BUY if self.is_buyer_maker else Order.SELL} ' \
               f'({self.taker_order_id}-{self.maker_order_id}) ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    def create_trade_trxs(self, ignore_fee=False, fake_trade: bool = False) -> FillOrderTrxs:
        trade_trx = self._create_trade_trx(fake=fake_trade)
        base_trx = self._create_base_trx(fake=fake_trade)

        # make sure sender and receiver wallets have same market
        assert trade_trx.sender.market == base_trx.receiver.market
        assert trade_trx.receiver.market == base_trx.sender.market

        taker_fee = self._create_fee_trx(self.taker_order, is_taker=True, fake=ignore_fee)
        maker_fee = self._create_fee_trx(self.maker_order, is_taker=False, fake=ignore_fee)

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
            is_buyer_maker=self.is_buyer_maker,
        )
        ReferralTrxTuple = namedtuple("ReferralTrx", "referral trx")
        return ReferralTrxTuple(referrals, ReferralTrx.get_trx_list(referrals))

    def _create_trade_trx(self, fake: bool = False) -> Trx:
        return Trx.transaction(
            sender=self.maker_order.wallet if self.taker_order.side == Order.BUY else self.taker_order.wallet,
            receiver=self.taker_order.wallet if self.taker_order.side == Order.BUY else self.maker_order.wallet,
            amount=self.amount,
            group_id=self.group_id,
            scope=Trx.TRADE,
            fake_trx=fake,
        )

    def _create_base_trx(self, fake: bool = False) -> Trx:
        return Trx.transaction(
            sender=self.maker_order.base_wallet if self.taker_order.side == Order.SELL else self.taker_order.base_wallet,
            receiver=self.taker_order.base_wallet if self.taker_order.side == Order.SELL else self.maker_order.base_wallet,
            amount=self.amount * self.price,
            group_id=self.group_id,
            scope=Trx.TRADE,
            fake_trx=fake,
        )

    def _create_fee_trx(self, order: Order, is_taker: bool, fake: bool = False) -> Trx:
        fee = order.symbol.taker_fee if is_taker else order.symbol.maker_fee

        fee_wallet = order.wallet if order.side == Order.BUY else order.base_wallet
        trx_amount = fee * (self.amount if order.side == Order.BUY else self.amount * self.price)

        if trx_amount:
            referral = self.taker_order.wallet.account.referred_by if is_taker else \
                self.maker_order.wallet.account.referred_by
            if referral:
                from market.models import ReferralTrx
                trx_amount *= Decimal(1) - (Decimal(ReferralTrx.REFERRAL_MAX_RETURN_PERCENT) / 100 - Decimal(
                    referral.owner_share_percent) / 100)

        return Trx.transaction(
            sender=fee_wallet,
            receiver=fee_wallet.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=fee_wallet.market),
            amount=trx_amount,
            group_id=self.group_id,
            scope=Trx.COMMISSION,
            fake_trx=fake
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
                "from market_fillorder where symbol_id = %s and created between %s and %s group by tf order by tf",
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

        fill_order = FillOrder(
            symbol=symbol,
            taker_order=taker_order,
            maker_order=maker_order,
            amount=amount,
            price=price,
            is_buyer_maker=(maker_order.side == Order.BUY),
            group_id=otc_trade.group_id,
            irt_value=base_irt_price * price * amount,
            trade_source=FillOrder.OTC
        )
        trade_trx_list = fill_order.create_trade_trxs(fake_trade=True)
        fill_order.set_amounts(trade_trx_list)
        from market.models import ReferralTrx
        referral_trx = fill_order.init_referrals(trade_trx_list)
        ReferralTrx.objects.bulk_create(list(filter(bool, referral_trx.referral)))
        fill_order.save()

        # updating trade_volume_irt of accounts
        accounts = [fill_order.maker_order.wallet.account, fill_order.taker_order.wallet.account]

        for account in accounts:
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + fill_order.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                check_prize_achievements(account)

        trade_trx_list.taker_fee.save()
        trade_trx_list.maker_fee.save()
