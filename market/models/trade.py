import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from django.conf import settings
from django.db import models
from django.db.models import F, CheckConstraint, Q, Sum, Max, Min
from django.utils import timezone

from ledger.models import OTCTrade, Asset, Wallet
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.precision import floor_precision, precision_to_step, decimal_to_str
from ledger.utils.price import get_tether_irt_price, BUY, get_trading_price_irt, get_trading_price_usdt, SELL
from ledger.utils.wallet_pipeline import WalletPipeline
from market.exceptions import NegativeGapRevenue
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


class Trade(models.Model):
    OTC, SYSTEM, SYSTEM_MAKER, SYSTEM_TAKER, MARKET = 'otc', 'system', 'sys-make', 'sys-take', 'market'
    SOURCE_CHOICES = (OTC, 'otc'), (MARKET, 'market'), (SYSTEM, 'system'), (SYSTEM_MAKER, SYSTEM_MAKER), \
                     (SYSTEM_TAKER, SYSTEM_TAKER)

    DONE, REVERT = 'd', 'r'
    STATUS_CHOICES = (DONE, 'done'), (REVERT, 'revert')

    created = models.DateTimeField(auto_now_add=True)
    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)

    market = models.CharField(
        max_length=8,
        choices=Wallet.MARKET_CHOICES,
    )

    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=DONE, db_index=True)
    side = models.CharField(max_length=8, choices=Order.ORDER_CHOICES)

    amount = get_amount_field()
    price = get_amount_field()
    is_maker = models.BooleanField()

    group_id = get_group_id_field(db_index=True)

    order_id = models.PositiveIntegerField(db_index=True)

    fee_amount = get_amount_field()

    base_irt_price = get_amount_field()
    base_usdt_price = get_amount_field(default=Decimal(1))

    trade_source = models.CharField(
        max_length=8,
        choices=SOURCE_CHOICES,
        db_index=True,
        default=MARKET
    )

    hedge_price = get_amount_field(null=True)
    gap_revenue = get_amount_field(null=True, default=Decimal(0))

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
                fee_amount__gte=0,
            ), name='check_market_trade_amounts', ),
        ]

    def __str__(self):
        return f'{self.symbol}-{self.side} ' \
               f'[p:{self.price:.2f}] (a:{self.amount:.5f})'

    @property
    def irt_value(self):
        return self.amount * self.price * self.base_irt_price

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
    def get_grouped_by_count(cls, symbol_id: int, interval_in_secs: int, start: datetime, end: datetime,
                             count_back=None):
        results = Trade.get_grouped_by_interval(symbol_id, interval_in_secs, start, end)
        if not count_back:
            return results
        # TODO: clean it later.
        try_count = 0
        while try_count < 3 and len(results) < count_back:
            try_count += 1
            shift = (end - start) * try_count
            older_results = Trade.get_grouped_by_interval(symbol_id, interval_in_secs, start - shift, end - shift)
            results = older_results[(len(results)) - count_back:] + results
        return results

    @classmethod
    def get_grouped_by_interval(cls, symbol_id: int, interval_in_secs: int, start: datetime, end: datetime):
        from market.utils.datetime_utils import ceil_date, floor_date
        if interval_in_secs <= 3600:
            round_func = ceil_date
            tf_shift = '30 min'
        else:
            round_func = floor_date
            tf_shift = '0 sec'
        start = round_func(start, seconds=interval_in_secs)
        end = round_func(end, seconds=interval_in_secs)
        return [
            {'timestamp': group.tf, 'open': group.open[1], 'high': group.high, 'low': group.low,
             'close': group.close[1], 'volume': group.volume}
            for group in cls.objects.raw(
                "select min(id) as id, "
                "min(array[id, price]) as open, max(array[id, price]) as close, "
                "max(price) as high, min(price) as low, "
                "sum(amount) as volume, "
                "(date_trunc('seconds', (created - (timestamptz 'epoch' - interval %s)) / %s) * %s + (timestamptz 'epoch' - interval %s)) as tf "
                "from market_trade where symbol_id = %s and side = 'buy' and status = 'd' and trade_source != 'otc' and created between %s and %s group by tf order by tf",
                [tf_shift, interval_in_secs, interval_in_secs, tf_shift, symbol_id, start, end]
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
        from market.utils.trade import register_transactions, TradesPair

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

        trades_pair = TradesPair.init_pair(
            taker_order=taker_order,
            maker_order=maker_order,
            amount=amount,
            price=price,
            base_irt_price=base_irt_price,
            trade_source=Trade.OTC,
            group_id=otc_trade.group_id,
        )

        register_transactions(pipeline, pair=trades_pair, fake_trade=True)

        for trade in trades_pair.trades:
            trade.set_gap_revenue()

        Trade.objects.bulk_create(trades_pair.trades)
        Trade.create_hedge_fiat_trxs(trades_pair.trades)

        # updating trade_volume_irt of accounts
        accounts = [trades_pair.maker_trade.account, trades_pair.taker_trade.account]

        for account in accounts:
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trades_pair.maker_trade.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(account, Task.TRADE)

    def get_fee_irt_value(self):
        if self.account.is_system():
            return 0

        if self.side == BUY:
            return self.fee_amount * self.price * self.base_irt_price
        else:
            return self.fee_amount * self.base_irt_price

    def set_gap_revenue(self):
        if settings.DEBUG_OR_TESTING:
            return

        self.gap_revenue = 0

        fee = self.get_fee_irt_value()

        if self.trade_source == self.MARKET or self.account.is_system():
            self.gap_revenue = fee
            return

        reverse_side = BUY if self.side == SELL else SELL

        base_asset = self.symbol.base_asset

        if base_asset.symbol == Asset.IRT:
            get_price = get_trading_price_irt
        elif base_asset.symbol == Asset.USDT:
            get_price = get_trading_price_usdt
        else:
            raise NotImplementedError

        self.hedge_price = get_price(self.symbol.asset.symbol, side=reverse_side, raw_price=True)

        if self.side == BUY:
            gap_price = self.price - self.hedge_price
        else:
            gap_price = self.hedge_price - self.price

        self.gap_revenue = gap_price * self.amount

        if base_asset.symbol == Asset.USDT:
            self.gap_revenue *= get_tether_irt_price(side=reverse_side)

        if self.gap_revenue < 0:
            raise NegativeGapRevenue

        self.gap_revenue += fee

    @staticmethod
    def get_account_orders_filled_price(account_id):
        return {
            trade['order_id']: (trade['sum_amount'], trade['sum_value']) for trade in
            Trade.objects.filter(account=account_id).annotate(
                value=F('amount') * F('price')
            ).values('order_id').annotate(sum_amount=Sum('amount'), sum_value=Sum('value')).values(
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
            if trade.symbol.base_asset.symbol == Asset.IRT and \
                    ((trade.is_maker and trade.trade_source == cls.SYSTEM_TAKER) or
                     (not trade.is_maker and trade.trade_source in [cls.OTC, cls.SYSTEM_MAKER])):

                hedge_price = get_trading_price_usdt(trade.symbol.asset.symbol, side=BUY, raw_price=True)

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
