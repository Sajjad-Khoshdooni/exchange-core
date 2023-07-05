import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import groupby
from math import floor, log10
from random import randrange, random
from time import time
from typing import Union
from uuid import uuid4

from django.conf import settings
from django.db import models, transaction
from django.db.models import F, Q, Max, Min, CheckConstraint, QuerySet, Sum, UniqueConstraint
from django.utils import timezone

from accounting.models import TradeRevenue
from accounts.models import Notification
from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.models.balance_lock import BalanceLock
from ledger.utils.external_price import get_external_price, BUY, SELL, SIDE_VERBOSE
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.otc import get_otc_spread, spread_to_multiplier
from ledger.utils.precision import floor_precision, round_down_to_exponent, round_up_to_exponent, decimal_to_str
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol, BaseTrade
from market.utils.price import set_last_trade_price

logger = logging.getLogger(__name__)


@dataclass
class MatchedTrades:
    trades: list = None
    trade_pairs: list = None
    filled_orders: list = None
    to_cancel_stoploss: list = None

    def __post_init__(self):
        if self.trades is None:
            self.trades = []
        if self.trade_pairs is None:
            self.trade_pairs = []
        if self.filled_orders is None:
            self.filled_orders = []
        if self.to_cancel_stoploss is None:
            self.to_cancel_stoploss = []

    def __bool__(self):
        return bool(self.trades and self.trade_pairs)


@dataclass
class TopOrder:
    side: str
    price: Decimal
    amount: Decimal


class OpenOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.NEW)


class CancelOrder(Exception):
    pass


class Order(models.Model):
    MARKET_BORDER = Decimal('1e-2')
    MIN_IRT_ORDER_SIZE = Decimal('1e5')
    MIN_USDT_ORDER_SIZE = Decimal(5)
    MAX_ORDER_DEPTH_SIZE_IRT = Decimal('9e7')
    MAX_ORDER_DEPTH_SIZE_USDT = Decimal(2500)
    MAKER_ORDERS_COUNT = 10 if settings.DEBUG_OR_TESTING else 50

    LIMIT, MARKET = 'limit', 'market'
    FILL_TYPE_CHOICES = [(LIMIT, LIMIT), (MARKET, MARKET)]

    TIME_IN_FORCE_OPTIONS = GTC, FOK, IOC = None, 'FOK', 'IOC'

    NEW, CANCELED, FILLED = 'new', 'canceled', 'filled'
    STATUS_CHOICES = [(NEW, NEW), (CANCELED, CANCELED), (FILLED, FILLED)]

    DEPTH = 'depth'
    BOT = 'bot'
    ORDINARY = None

    TYPE_CHOICES = ((DEPTH, 'depth'), (BOT, 'bot'), (ORDINARY, 'ordinary'))

    type = models.CharField(
        max_length=8,
        choices=TYPE_CHOICES,
        null=True,
        blank=True
    )

    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='orders')

    symbol = models.ForeignKey(PairSymbol, on_delete=models.PROTECT)
    amount = get_amount_field()
    filled_amount = get_amount_field(default=Decimal(0))
    price = get_amount_field()
    side = models.CharField(max_length=8, choices=BaseTrade.SIDE_CHOICES)
    fill_type = models.CharField(max_length=8, choices=FILL_TYPE_CHOICES)
    status = models.CharField(default=NEW, max_length=8, choices=STATUS_CHOICES)

    group_id = get_group_id_field(null=True)

    client_order_id = models.CharField(max_length=36, null=True, blank=True)

    stop_loss = models.ForeignKey(to='market.StopLoss', on_delete=models.SET_NULL, null=True, blank=True)

    time_in_force = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        choices=[(GTC, 'GTC'), (FOK, 'FOK'), (IOC, 'IOC')]
    )

    def __str__(self):
        return f'({self.id}) {self.symbol}-{self.side} [p:{self.price:.2f}] (u:{self.unfilled_amount:.5f}/{self.amount:.5f})'

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'type', 'status', 'created']),
            models.Index(fields=['symbol', 'status']),
            models.Index(name='market_new_orders_price_idx', fields=['price'], condition=Q(status='new')),
        ]
        constraints = [
            CheckConstraint(check=Q(filled_amount__lte=F('amount')), name='check_filled_amount', ),
            CheckConstraint(check=Q(amount__gte=0, filled_amount__gte=0, price__gte=0),
                            name='check_market_order_amounts', ),
            UniqueConstraint(
                fields=('account', 'client_order_id', 'status'),
                condition=Q(status='new'),
                name='unique_client_order_id_new_order'
            ),
            UniqueConstraint(
                name='market_order_unique_group_id',
                fields=('group_id', 'status'),
            ),
            UniqueConstraint(
                name='market_order_unique_stop_loss',
                fields=('stop_loss', 'status'),
            ),
        ]

    objects = models.Manager()
    open_objects = OpenOrderManager()

    def cancel(self):
        # to increase performance
        if self.status != self.NEW:
            return

        from market.utils.redis import MarketStreamCache
        with WalletPipeline() as pipeline:  # type: WalletPipeline
            PairSymbol.objects.select_for_update().get(id=self.symbol_id)
            order = Order.objects.filter(status=Order.NEW, id=self.id).first()

            if not order:
                return

            order.status = self.CANCELED
            order.save(update_fields=['status'])
            pipeline.release_lock(key=order.group_id)

        MarketStreamCache().execute(self.symbol, [order], side=order.side, canceled=True)

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(
            account=self.wallet.account, market=self.wallet.market, variant=self.wallet.variant
        )

    @property
    def unfilled_amount(self):
        amount = self.amount - self.filled_amount
        return floor_precision(amount, self.symbol.step_size)

    @staticmethod
    def get_opposite_side(side):
        return SELL if side.lower() == BUY else BUY

    @staticmethod
    def get_order_by(side):
        return (lambda order: (-order.price, order.id)) if side == BUY else \
            (lambda order: (order.price, order.id))

    @classmethod
    def cancel_orders(cls, to_cancel_orders: QuerySet):
        # for order in to_cancel_orders.filter(status=Order.NEW):
        for order in to_cancel_orders:
            order.cancel()

    @staticmethod
    def get_price_filter(price, side):
        return {'price__lte': price} if side == BUY else {'price__gte': price}

    @classmethod
    def get_to_lock_wallet(cls, wallet, base_wallet, side) -> Wallet:
        return base_wallet if side == BUY else wallet

    @classmethod
    def get_to_lock_amount(cls, amount: Decimal, price: Decimal, side: str) -> Decimal:
        return amount * price if side == BUY else amount

    def submit(self, pipeline: WalletPipeline, is_stop_loss: bool = False) -> MatchedTrades:
        overriding_fill_amount = None
        if is_stop_loss:
            if self.side == BUY:
                locked_amount = BalanceLock.objects.get(key=self.group_id).amount
                if locked_amount < self.amount * self.price:
                    overriding_fill_amount = floor_precision(locked_amount / self.price, self.symbol.step_size)
                    if not overriding_fill_amount:
                        raise CancelOrder('Overriding fill amount is zero')
        else:
            overriding_fill_amount = self.acquire_lock(pipeline)

        matched_trades = self.make_match(pipeline, overriding_fill_amount)
        to_cancel_stop_loss = []
        if matched_trades:
            # trigger stop loss
            min_price = min(map(lambda t: t.price, matched_trades.trades))
            max_price = max(map(lambda t: t.price, matched_trades.trades))
            from market.models import StopLoss
            to_trigger_stop_loss_qs = StopLoss.not_triggered_objects.filter(
                Q(side=BUY, trigger_price__lte=max_price) | Q(side=SELL, trigger_price__gte=min_price),
                symbol=self.symbol,
            ).exclude(id=self.stop_loss_id)
            log_prefix = 'MM %s {%s}: ' % (self.symbol.name, self.id)
            logger.info(log_prefix + f'to trigger stop loss: {list(to_trigger_stop_loss_qs.values_list("id", flat=True))} {timezone.now()}')
            for stop_loss in to_trigger_stop_loss_qs:
                from market.utils.order_utils import trigger_stop_loss
                triggered_price = min_price if stop_loss.side == SELL else max_price
                logger.info(log_prefix + f'triggering stop loss on {self.symbol} ({stop_loss.id}, {stop_loss.side}) at {triggered_price}, {timezone.now()}')
                to_cancel = trigger_stop_loss(pipeline, stop_loss, triggered_price)
                if to_cancel:
                    to_cancel_stop_loss.append(to_cancel)
            if to_cancel_stop_loss:
                matched_trades.to_cancel_stoploss = to_cancel_stop_loss
        return matched_trades

    def acquire_lock(self, pipeline: WalletPipeline):
        to_lock_wallet = self.get_to_lock_wallet(self.wallet, self.base_wallet, self.side)
        lock_amount = Order.get_to_lock_amount(self.amount, self.price, self.side)

        if self.side == BUY and self.fill_type == Order.MARKET:
            free_amount = to_lock_wallet.get_free()
            if free_amount > Decimal('0.95') * lock_amount:
                lock_amount = min(lock_amount, free_amount)

        to_lock_wallet.has_balance(lock_amount, raise_exception=True)

        pipeline.new_lock(key=self.group_id, wallet=to_lock_wallet, amount=lock_amount, reason=WalletPipeline.TRADE)

        if self.side == BUY and self.fill_type == Order.MARKET:
            return floor_precision(lock_amount / self.price, self.symbol.step_size)

    def release_lock(self, pipeline: WalletPipeline, release_amount: Decimal):
        release_amount = Order.get_to_lock_amount(release_amount, self.price, self.side)
        pipeline.release_lock(key=self.group_id, amount=release_amount)

    def make_match(self, pipeline: WalletPipeline, overriding_fill_amount: Union[Decimal, None]) -> MatchedTrades:
        from market.utils.trade import register_transactions, TradesPair
        from market.models import Trade

        symbol = PairSymbol.objects.select_for_update().get(id=self.symbol_id)

        log_prefix = 'MM %s {%s}: ' % (symbol.name, self.id)

        logger.info(log_prefix + f'make match started... {overriding_fill_amount} {timezone.now()}')

        maker_side = self.get_opposite_side(self.side)

        matching_orders = Order.open_objects.filter(symbol=symbol, side=maker_side)
        if maker_side == BUY:
            matching_orders = matching_orders.filter(price__gte=self.price).order_by('-price', 'id')
        else:
            matching_orders = matching_orders.filter(price__lte=self.price).order_by('price', 'id')

        unfilled_amount = overriding_fill_amount or self.unfilled_amount

        if self.time_in_force == self.FOK:
            total_maker_amounts = matching_orders.aggregate(
                total_amount=Sum(F('amount') - F('filled_amount'))
            )['total_amount'] or 0

            if unfilled_amount > total_maker_amounts:
                self.status = Order.CANCELED
                pipeline.release_lock(self.group_id)
                self.save(update_fields=['status'])
                return MatchedTrades()

        matching_orders = list(matching_orders)
        logger.info(log_prefix + f'make match finished fetching matching orders {len(matching_orders)} {timezone.now()}')

        if not matching_orders:
            return MatchedTrades()

        trades = []
        filled_orders = []

        tether_irt = get_external_price(coin=Asset.USDT, base_coin=Asset.IRT, side=BUY)

        taker_is_system = self.wallet.account.is_system()

        for maker_order in matching_orders:
            trade_price = maker_order.price

            match_amount = min(maker_order.unfilled_amount, unfilled_amount)
            if match_amount <= 0:
                continue

            base_irt_price = 1
            base_usdt_price = 1

            if symbol.base_asset.symbol == Asset.USDT:
                base_irt_price = tether_irt
            else:
                base_usdt_price = 1 / tether_irt

            maker_is_system = maker_order.wallet.account.is_system()

            source_map = {
                (True, True): Trade.SYSTEM,
                (True, False): Trade.SYSTEM_MAKER,
                (False, True): Trade.SYSTEM_TAKER,
                (False, False): Trade.MARKET,
            }

            if settings.ZERO_USDT_HEDGE and symbol.name == 'USDTIRT':
                maker_is_trader = maker_order.account.id == settings.TRADER_ACCOUNT_ID
                taker_is_trader = self.account.id == settings.TRADER_ACCOUNT_ID
                trade_source = source_map[maker_is_trader, taker_is_trader]
            else:
                trade_source = source_map[maker_is_system, taker_is_system]

            trades_pair = TradesPair.init_pair(
                taker_order=self,
                maker_order=maker_order,
                amount=match_amount,
                price=trade_price,
                base_irt_price=base_irt_price,
                base_usdt_price=base_usdt_price,
                trade_source=trade_source,
                group_id=uuid4()
            )

            if not taker_is_system:
                Notification.send(
                    recipient=self.wallet.account.user,
                    title='معامله {} انجام شد'.format(symbol),
                    message='{side} {amount} {coin}'.format(
                        amount=match_amount,
                        side=SIDE_VERBOSE[self.side],
                        coin=symbol.asset.name_fa
                    )
                )

            if not maker_is_system:
                Notification.send(
                    recipient=maker_order.wallet.account.user,
                    title='معامله {} انجام شد'.format(maker_order.symbol),
                    message='{side} {amount} {coin}'.format(
                        amount=match_amount,
                        side=SIDE_VERBOSE[maker_side],
                        coin=symbol.asset.name_fa
                    )
                )

            self.release_lock(pipeline, match_amount)
            maker_order.release_lock(pipeline, match_amount)

            register_transactions(pipeline, pair=trades_pair)

            trades.extend(trades_pair.trades)

            self.update_filled_amount((self.id, maker_order.id), match_amount)

            unfilled_amount -= match_amount
            if match_amount == maker_order.unfilled_amount:  # unfilled_amount reduced in DB but not updated here :)
                with transaction.atomic():
                    maker_order.status = Order.FILLED
                    maker_order.save(update_fields=['status'])
                    filled_orders.append(maker_order)

            if unfilled_amount == 0:
                self.status = Order.FILLED

                if self.fill_type == Order.MARKET:
                    pipeline.release_lock(self.group_id)

                self.save(update_fields=['status'])
                break

        if (self.fill_type == Order.MARKET or self.time_in_force == self.IOC) and self.status == Order.NEW:
            self.status = Order.CANCELED
            pipeline.release_lock(self.group_id)
            self.save(update_fields=['status'])

        trades = Trade.objects.bulk_create(trades)
        trade_pairs = list(zip(trades[0::2], trades[1::2]))

        if trades:
            symbol.last_trade_time = timezone.now()
            symbol.last_trade_price = trades[-1].price
            symbol.save(update_fields=['last_trade_time', 'last_trade_price'])
            set_last_trade_price(symbol)
            trade_revenues = []
            for maker_trade, taker_trade in trade_pairs:
                if maker_trade.trade_source in (Trade.SYSTEM_MAKER, Trade.SYSTEM_TAKER):
                    hedge_key = f'tr-{taker_trade.id}' \
                        if settings.ZERO_USDT_HEDGE and symbol.name == 'USDTIRT' else \
                        f'mm-{taker_trade.id}'

                    ignore_trade_value = taker_trade.trade_source == Trade.SYSTEM_TAKER and \
                                         taker_trade.account_id == settings.OTC_ACCOUNT_ID

                    trade_revenues.append(TradeRevenue.new(
                        user_trade=taker_trade if maker_trade.trade_source == Trade.SYSTEM_MAKER else maker_trade,
                        group_id=taker_trade.group_id,
                        source=TradeRevenue.MAKER if maker_trade.trade_source == Trade.SYSTEM_TAKER else TradeRevenue.TAKER,
                        hedge_key=hedge_key,
                        ignore_trade_value=ignore_trade_value
                    ))
                elif maker_trade.trade_source == Trade.MARKET:
                    for t in (maker_trade, taker_trade):
                        trade_revenues.append(
                            TradeRevenue.new(
                                user_trade=t,
                                group_id=t.group_id,
                                source=TradeRevenue.USER,
                                hedge_key=''
                            )
                        )
            if trade_revenues:
                TradeRevenue.objects.bulk_create(trade_revenues)

        # updating trade_volume_irt of accounts
        for trade in trades:
            account = trade.account
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trade.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()

                from gamify.utils import check_prize_achievements, Task
                check_prize_achievements(account, Task.TRADE)

        logger.info(log_prefix + f'make match finished.  {timezone.now()}')
        return MatchedTrades(trades=trades, trade_pairs=trade_pairs, filled_orders=filled_orders)

    @classmethod
    def get_formatted_orders(cls, open_orders, symbol: PairSymbol, order_type: str):
        filtered_orders = list(filter(lambda o: o['side'] == order_type, open_orders))
        aggregated_orders = cls.get_aggregated_orders(symbol, *filtered_orders)

        sort_func = (lambda o: -Decimal(o['price'])) if order_type == BUY else (lambda o: Decimal(o['price']))

        return sorted(aggregated_orders, key=sort_func)

    @staticmethod
    def get_aggregated_orders(symbol: PairSymbol, *orders):
        key_func = (lambda o: o['price'])
        grouped_by_price = [(i[0], list(i[1])) for i in groupby(sorted(orders, key=key_func), key=key_func)]
        return [{
            'price': format(price, 'f'),
            'amount': decimal_to_str(floor_precision(sum(map(lambda i: i['unfilled_amount'], price_orders)), symbol.step_size)),
            'depth': Order.get_depth_value(sum(map(lambda i: i['unfilled_amount'], price_orders)), price,
                                           symbol.base_asset.symbol),
            'total': decimal_to_str(floor_precision(sum(map(lambda i: i['unfilled_amount'] * price, price_orders)), 0))
        } for price, price_orders in grouped_by_price]

    @staticmethod
    def get_depth_value(amount, price, base_asset: str):
        if base_asset == Asset.IRT:
            return str(min(100, floor_precision((amount * price) / Order.MAX_ORDER_DEPTH_SIZE_IRT * 100, 0)))
        if base_asset == Asset.USDT:
            return str(min(100, floor_precision((amount * price) / Order.MAX_ORDER_DEPTH_SIZE_USDT * 100, 0)))

    @staticmethod
    def quantize_values(symbol: PairSymbol, open_orders):
        return [{
            'side': order['side'],
            'price': floor_precision(order['price'], symbol.tick_size),
            'unfilled_amount': floor_precision(order['unfilled_amount'], symbol.step_size),
        } for order in open_orders]

    # Market Maker related methods
    @staticmethod
    def get_rounding_precision(number, max_precision):
        power = floor(log10(number))
        precision = min(3, -power / 3) if power > 2 else (2 - power)
        return int(min(precision, max_precision))

    @classmethod
    def update_filled_amount(cls, order_ids, match_amount):
        Order.objects.filter(id__in=order_ids).update(filled_amount=F('filled_amount') + match_amount)
        from market.models import StopLoss
        StopLoss.objects.filter(order__id__in=order_ids).update(filled_amount=F('filled_amount') + match_amount)

    @classmethod
    def get_market_price(cls, symbol, side):
        open_orders = Order.open_objects.filter(symbol_id=symbol.id, side=side, fill_type=Order.LIMIT)
        top_order = open_orders.aggregate(top_price=Max('price')) if side == BUY else \
            open_orders.aggregate(top_price=Min('price'))
        if not top_order['top_price']:
            return
        market_price = top_order['top_price'] * (Decimal(1) - cls.MARKET_BORDER) if side == BUY else \
            top_order['top_price'] * (Decimal(1) + cls.MARKET_BORDER)
        return market_price

    @classmethod
    def get_top_depth_prices(cls, symbol_id, scope=''):
        from market.utils.redis import get_top_prices
        top_prices = get_top_prices(symbol_id, scope=scope)
        if not top_prices:
            top_prices = defaultdict(lambda: Decimal())
            for depth in Order.open_objects.filter(symbol_id=symbol_id, type=Order.DEPTH).values('side').annotate(
                    max_price=Max('price'), min_price=Min('price')
            ):
                top_prices[depth['side']] = (depth['max_price'] if depth['side'] == BUY else depth['min_price']) \
                                            or Decimal()
        return top_prices

    @classmethod
    def get_top_price(cls, symbol_id, side):
        agg_func = Max if side == BUY else Min
        top_price = cls.open_objects.filter(
            symbol_id=symbol_id, side=side
        ).aggregate(top_price=agg_func('price'))['top_price']
        return top_price

    @classmethod
    def get_top_price_amount(cls, symbol_id, side):
        agg_func = Max if side == BUY else Min
        top_price = cls.open_objects.filter(
            symbol_id=symbol_id, side=side
        ).aggregate(top_price=agg_func('price'))['top_price']
        if not top_price:
            return None
        unfilled_amount = cls.open_objects.filter(
            symbol_id=symbol_id, side=side, price=top_price
        ).annotate(unfilled_amount=F('amount') - F('filled_amount')).aggregate(
            total_amount=Sum('unfilled_amount')
        )['total_amount']
        return TopOrder(side=side, price=top_price, amount=unfilled_amount)
