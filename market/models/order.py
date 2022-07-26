import logging
from collections import defaultdict
from decimal import Decimal
from itertools import groupby
from math import floor, log10
from random import randrange, random
from uuid import uuid4

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import Sum, F, Q, Max, Min, CheckConstraint, QuerySet

from accounts.gamification.gamify import check_prize_achievements
from accounts.models import Notification
from ledger.models import Wallet
from ledger.models.asset import Asset
from ledger.utils.fields import get_amount_field, get_group_id_field
from ledger.utils.precision import floor_precision, round_down_to_exponent, round_up_to_exponent
from ledger.utils.price import get_trading_price_irt, IRT, USDT, get_trading_price_usdt, get_tether_irt_price
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol
from market.models.referral_trx import ReferralTrx
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class OpenOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.NEW)


class CancelOrder(Exception):
    pass


class Order(models.Model):
    MARKET_BORDER = Decimal('1e-2')
    MIN_IRT_ORDER_SIZE = Decimal('1e5')
    MIN_USDT_ORDER_SIZE = Decimal(5)
    MAX_ORDER_DEPTH_SIZE_IRT = Decimal('2e7')
    MAX_ORDER_DEPTH_SIZE_USDT = Decimal(1000)
    MAKER_ORDERS_COUNT = 10 if settings.DEBUG_OR_TESTING else 50

    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    LIMIT, MARKET = 'limit', 'market'
    FILL_TYPE_CHOICES = [(LIMIT, LIMIT), (MARKET, MARKET)]

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

    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='orders')
    created = models.DateTimeField(auto_now_add=True)

    symbol = models.ForeignKey(PairSymbol, on_delete=models.CASCADE)
    amount = get_amount_field()
    filled_amount = get_amount_field(default=Decimal(0))
    price = get_amount_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)
    fill_type = models.CharField(max_length=8, choices=FILL_TYPE_CHOICES)
    status = models.CharField(default=NEW, max_length=8, choices=STATUS_CHOICES)

    group_id = get_group_id_field(null=True)

    client_order_id = models.CharField(max_length=36, null=True, blank=True)

    stop_loss = models.ForeignKey(to='market.StopLoss', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'({self.id}) {self.symbol}-{self.side} [p:{self.price:.2f}] (a:{self.unfilled_amount:.5f}/{self.amount:.5f})'

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'type', 'status', 'created']),
            models.Index(fields=['symbol', 'status']),
            models.Index(name='market_new_orders_price_idx', fields=['price'], condition=Q(status='new')),
        ]
        constraints = [
            CheckConstraint(check=Q(filled_amount__lte=F('amount')), name='check_filled_amount', ),
            CheckConstraint(check=Q(amount__gte=0, filled_amount__gte=0, price__gte=0), name='check_market_order_amounts', ),
        ]

    objects = models.Manager()
    open_objects = OpenOrderManager()

    def cancel(self):
        self.refresh_from_db()

        if self.status == self.FILLED:
            return

        with WalletPipeline() as pipeline:  # type: WalletPipeline
            self.status = self.CANCELED
            self.save(update_fields=['status'])
            pipeline.release_lock(key=self.group_id)

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(
            self.wallet.account, self.wallet.market, variant=self.wallet.variant
        )

    @property
    def filled_price(self):
        fills_amount, fills_value = self.trades.all().annotate(
            value=F('amount') * F('price')).aggregate(sum_amount=Sum('amount'), sum_value=Sum('value')).values()
        amount = Decimal((fills_amount or 0))
        if not amount:
            return None
        price = Decimal((fills_value or 0)) / amount
        return floor_precision(price, self.symbol.tick_size)

    @property
    def unfilled_amount(self):
        amount = self.amount - self.filled_amount
        return floor_precision(amount, self.symbol.step_size)

    @staticmethod
    def matching_orders_filter(side, price, op):
        return(lambda order: order.side == side and order.price >= price) if op == 'gte' else \
                (lambda order: order.side == side and order.price <= price)

    @staticmethod
    def get_opposite_side(side):
        return Order.SELL if side.lower() == Order.BUY else Order.BUY

    @staticmethod
    def get_order_by(side):
        return (lambda order: (-order.price, order.id)) if side == Order.BUY else \
                (lambda order: (order.price, order.id))

    @classmethod
    def cancel_orders(cls, to_cancel_orders: QuerySet):
        to_cancel_orders = list(to_cancel_orders.exclude(status=cls.FILLED))

        for order in to_cancel_orders:
            order.cancel()

    @staticmethod
    def get_price_filter(price, side):
        return {'price__lte': price} if side == Order.BUY else {'price__gte': price}

    @staticmethod
    def get_maker_price(symbol: PairSymbol.IdName, side: str, loose_factor=Decimal(1), gap=None):
        if symbol.name.endswith(IRT):
            base_symbol = IRT
            get_trading_price = get_trading_price_irt
        elif symbol.name.endswith(USDT):
            base_symbol = USDT
            get_trading_price = get_trading_price_usdt
        else:
            raise NotImplementedError('Invalid trading symbol')

        coin = symbol.name.split(base_symbol)[0]
        boundary_price = get_trading_price(coin, side, gap=gap)

        precision = Order.get_rounding_precision(boundary_price, symbol.tick_size)
        # use bi-direction in roundness to avoid risky bid ask spread
        if side == Order.BUY:
            return round_down_to_exponent(boundary_price * loose_factor, precision)
        else:
            return round_up_to_exponent(boundary_price / loose_factor, precision)

    @classmethod
    def get_to_lock_wallet(cls, wallet, base_wallet, side) -> Wallet:
        return base_wallet if side == Order.BUY else wallet

    @classmethod
    def get_to_lock_amount(cls, amount: Decimal, price: Decimal, side: str) -> Decimal:
        return amount * price if side == Order.BUY else amount

    def submit(self, pipeline: WalletPipeline, check_balance: bool = True):
        self.acquire_lock(pipeline, check_balance=check_balance)
        self.make_match(pipeline)

    def acquire_lock(self, pipeline: WalletPipeline, check_balance: bool = True):
        to_lock_wallet = self.get_to_lock_wallet(self.wallet, self.base_wallet, self.side)
        lock_amount = Order.get_to_lock_amount(self.amount, self.price, self.side)

        if check_balance:
            to_lock_wallet.has_balance(lock_amount, raise_exception=True)

        pipeline.new_lock(key=self.group_id, wallet=to_lock_wallet, amount=lock_amount, reason=WalletPipeline.TRADE)

    def release_lock(self, pipeline: WalletPipeline, release_amount: Decimal):
        release_amount = Order.get_to_lock_amount(release_amount, self.price, self.side)
        pipeline.release_lock(key=self.group_id, amount=release_amount)

    def make_match(self, pipeline: WalletPipeline):
        key = 'mm-cc-%s' % self.symbol.name
        log_prefix = 'MM %s: ' % self.symbol.name

        logger.info(log_prefix + 'make match started...')

        from market.models import Trade
        # lock symbol open orders
        open_orders = list(Order.open_objects.select_for_update().filter(symbol=self.symbol))

        logger.info(log_prefix + 'make match danger zone')

        # if cache.get(key):
        #     logger.info(log_prefix + 'concurrent detected!')
        #     raise Exception('Concurrent make match!')

        cache.set(key, 1, 10)

        to_cancel_orders = Order.open_objects.filter(
            symbol=self.symbol, cancel_request__isnull=False
        )
        self.cancel_orders(to_cancel_orders)

        opp_side = self.get_opposite_side(self.side)

        operator = 'lte' if self.side == Order.BUY else 'gte'
        matching_orders = list(sorted(filter(
            self.matching_orders_filter(side=opp_side, price=self.price, op=operator), open_orders
        ), key=self.get_order_by(opp_side)))

        unfilled_amount = self.unfilled_amount

        trades = []
        referrals = []

        to_hedge_amount = Decimal(0)

        for matching_order in matching_orders:
            trade_price = matching_order.price
            if (self.side == Order.BUY and self.price < trade_price) or (
                    self.side == Order.SELL and self.price > trade_price
            ):
                continue

            match_amount = min(matching_order.unfilled_amount, unfilled_amount)
            if match_amount <= 0:
                continue

            base_irt_price = 1

            if self.symbol.base_asset.symbol == Asset.USDT:
                try:
                    base_irt_price = get_tether_irt_price(self.side)
                except:
                    base_irt_price = 27000

            taker_is_system = self.wallet.account.is_system()
            maker_is_system = matching_order.wallet.account.is_system()

            source_map = {
                (True, True): Trade.SYSTEM,
                (True, False): Trade.SYSTEM_MAKER,
                (False, True): Trade.SYSTEM_TAKER,
                (False, False): Trade.MARKET,
            }

            trade_source = source_map[maker_is_system, taker_is_system]

            trades_pair = Trade.init_pair(
                symbol=self.symbol,
                taker_order=self,
                maker_order=matching_order,
                amount=match_amount,
                price=trade_price,
                irt_value=base_irt_price * trade_price * match_amount,
                trade_source=trade_source,
                group_id=uuid4()
            )

            if not taker_is_system:
                Notification.send(
                    recipient=self.wallet.account.user,
                    title='معامله {}'.format(self.symbol),
                    message=( 'مقدار {symbol} {amount} معامله شد.').format(amount=match_amount, symbol=self.symbol)
                )

            if not maker_is_system:
                Notification.send(
                    recipient=matching_order.wallet.account.user,
                    title='معامله {}'.format(matching_order.symbol),
                    message=('مقدار {symbol} {amount} معامله شد.').format(
                        amount=match_amount,
                        symbol=matching_order.symbol
                    )
                )

            if trade_source == Trade.SYSTEM_TAKER and not self.wallet.account.primary:
                if trades_pair.maker.gap_revenue < trades_pair.maker.irt_value * Decimal('0.0015'):
                    raise CancelOrder('Non primary system is being taker! dangerous.')

            self.release_lock(pipeline, match_amount)
            matching_order.release_lock(pipeline, match_amount)

            trade_trxs = trades_pair.maker.create_trade_trxs(pipeline, self)

            tether_irt = Decimal(1) if self.symbol.base_asset.symbol == self.symbol.base_asset.IRT else \
                get_tether_irt_price(self.BUY)
            for trade in trades_pair:
                trade.set_amounts(trade_trxs)
                fee_trx = trade_trxs.maker_fee if trade.is_maker else trade_trxs.taker_fee
                referrals.append(trade.create_referral(pipeline, fee_trx, tether_irt))

            trades.extend(trades_pair)

            self.update_filled_amount((self.id, matching_order.id), match_amount)

            if self.wallet.account.is_ordinary_user() != matching_order.wallet.account.is_ordinary_user():
                ordinary_order = self if self.type == Order.ORDINARY else matching_order

                if ordinary_order.side == Order.SELL:
                    to_hedge_amount -= match_amount
                else:
                    to_hedge_amount += match_amount

            unfilled_amount -= match_amount
            if match_amount == matching_order.unfilled_amount:  # unfilled_amount reduced in DB but not updated here :)
                matching_order.status = Order.FILLED
                matching_order.save(update_fields=['status'])

            if unfilled_amount == 0:
                self.status = Order.FILLED
                self.save(update_fields=['status'])
                break

        if to_hedge_amount != 0:
            side = Order.BUY

            if to_hedge_amount < 0:
                to_hedge_amount = -to_hedge_amount
                side = Order.SELL

            placed_hedge_order = ProviderOrder.try_hedge_for_new_order(
                asset=self.wallet.asset,
                side=side,
                amount=to_hedge_amount,
                scope=ProviderOrder.TRADE
            )

            if not placed_hedge_order:
                raise Exception('failed placing hedge order')

        if self.fill_type == Order.MARKET and self.status == Order.NEW:
            self.status = Order.CANCELED
            pipeline.release_lock(self.group_id)
            self.save(update_fields=['status'])

        ReferralTrx.objects.bulk_create(filter(lambda referral: referral, referrals))
        Trade.objects.bulk_create(trades)

        # updating trade_volume_irt of accounts
        for trade in trades:
            account = trade.account
            if not account.is_system():
                account.trade_volume_irt = F('trade_volume_irt') + trade.irt_value
                account.save(update_fields=['trade_volume_irt'])
                account.refresh_from_db()
                check_prize_achievements(account)
            
            cache.delete(key)
            logger.info(log_prefix + 'make match finished.')

    @classmethod
    def get_formatted_orders(cls, open_orders, symbol: PairSymbol, order_type: str):
        filtered_orders = list(filter(lambda o: o['side'] == order_type, open_orders))
        aggregated_orders = cls.get_aggregated_orders(symbol, *filtered_orders)

        sort_func = (lambda o: -Decimal(o['price'])) if order_type == Order.BUY else (lambda o: Decimal(o['price']))

        return sorted(aggregated_orders, key=sort_func)

    @staticmethod
    def get_aggregated_orders(symbol: PairSymbol, *orders):
        key_func = (lambda o: o['price'])
        grouped_by_price = [(i[0], list(i[1])) for i in groupby(sorted(orders, key=key_func), key=key_func)]
        return [{
            'price': str(price),
            'amount': str(floor_precision(sum(map(lambda i: i['unfilled_amount'], price_orders)), symbol.step_size)),
            'depth': Order.get_depth_value(sum(map(lambda i: i['unfilled_amount'], price_orders)), price,
                                           symbol.base_asset.symbol),
            'total': str(floor_precision(sum(map(lambda i: i['unfilled_amount'] * price, price_orders)), 0))
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

    @staticmethod
    def init_maker_order(symbol: PairSymbol.IdName, side, maker_price: Decimal, market=Wallet.SPOT):
        symbol_instance = PairSymbol.objects.get(id=symbol.id)
        if random() < 0.6:
            amount_factor = Decimal(randrange(2, 15) / Decimal(100))
        else:
            amount_factor = Decimal(randrange(10, 20) / Decimal(10))
        maker_amount = symbol_instance.maker_amount * amount_factor * Decimal(randrange(80, 120) / Decimal(100))
        precision = Order.get_rounding_precision(maker_amount, symbol_instance.step_size)
        amount = round_down_to_exponent(maker_amount, precision)
        wallet = symbol_instance.asset.get_wallet(settings.SYSTEM_ACCOUNT_ID, market=market)
        precision = Order.get_rounding_precision(maker_price, symbol_instance.tick_size)
        return Order(
            type=Order.DEPTH,
            wallet=wallet,
            symbol=symbol_instance,
            amount=amount,
            price=round_down_to_exponent(maker_price, precision),
            side=side,
            fill_type=Order.LIMIT
        )

    @classmethod
    def init_top_maker_order(cls, symbol, side, maker_price, best_order, market=Wallet.SPOT):
        if not maker_price:
            logger.warning(f'cannot calculate maker price for {symbol.name} {side}')
            return

        loose_factor = Decimal('1.001') if side == Order.BUY else 1 / Decimal('1.001')
        if not best_order or \
                (side == Order.BUY and maker_price > best_order * loose_factor) or \
                (side == Order.SELL and maker_price < best_order * loose_factor):
            return cls.init_maker_order(symbol, side, maker_price, market)

    @classmethod
    def cancel_invalid_maker_orders(cls, symbol: PairSymbol.IdName, top_prices, gap=None, order_type=DEPTH):
        for side in (Order.BUY, Order.SELL):
            price = cls.get_maker_price(symbol, side, loose_factor=Decimal('1.001'), gap=gap)
            if (side == Order.BUY and Decimal(top_prices[side]) <= price) or (
                    side == Order.SELL and Decimal(top_prices[side]) >= price):
                logger.info(f'{order_type} {side} ignore cancels with price: {price} top: {top_prices[side]}')
                continue

            invalid_orders = Order.open_objects.select_for_update().filter(
                symbol_id=symbol.id, side=side, type=order_type
            ).exclude(**cls.get_price_filter(price, side))

            cls.cancel_orders(invalid_orders)

            logger.info(f'{order_type} {side} cancels with price: {price}')

    @classmethod
    def cancel_waste_maker_orders(cls, symbol: PairSymbol.IdName, open_orders_count):
        for side in (Order.BUY, Order.SELL):
            wasted_orders = Order.open_objects.filter(symbol_id=symbol.id, side=side, type=Order.DEPTH)
            wasted_orders = wasted_orders.order_by('price') if side == Order.BUY else wasted_orders.order_by('-price')
            cancel_count = int(open_orders_count[side]) - Order.MAKER_ORDERS_COUNT

            logger.info(f'maker {symbol.name} {side}: wasted={len(wasted_orders)} cancels={cancel_count}')

            if cancel_count > 0:
                cls.cancel_orders(
                    Order.objects.filter(id__in=wasted_orders.values_list('id', flat=True)[:cancel_count])
                )
                logger.info(f'maker {side} cancel wastes')

    @classmethod
    def update_filled_amount(cls, order_ids, match_amount):
        Order.objects.filter(id__in=order_ids).update(filled_amount=F('filled_amount') + match_amount)
        from market.models import StopLoss
        StopLoss.objects.filter(order__id__in=order_ids).update(filled_amount=F('filled_amount') + match_amount)

    @classmethod
    def get_market_price(cls, symbol, side):
        open_orders = Order.open_objects.filter(symbol_id=symbol.id, side=side, fill_type=Order.LIMIT)
        top_order = open_orders.aggregate(top_price=Max('price')) if side == Order.BUY else \
            open_orders.aggregate(top_price=Min('price'))
        if not top_order['top_price']:
            return
        market_price = top_order['top_price'] * (Decimal(1) - cls.MARKET_BORDER) if side == Order.BUY else \
            top_order['top_price'] * (Decimal(1) + cls.MARKET_BORDER)
        return market_price

    @classmethod
    def get_top_prices(cls, symbol_id):
        from market.utils.redis import get_top_prices
        top_prices = get_top_prices(symbol_id)
        if not top_prices:
            top_prices = defaultdict(lambda: Decimal())
            for depth in Order.open_objects.filter(symbol_id=symbol_id).values('side').annotate(max_price=Max('price'),
                                                                                                min_price=Min('price')):
                top_prices[depth['side']] = (depth['max_price'] if depth['side'] == Order.BUY else depth[
                    'min_price']) or Decimal()
        return top_prices
