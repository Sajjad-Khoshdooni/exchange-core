import logging
from decimal import Decimal
from itertools import groupby
from random import random
from uuid import uuid4

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, F

from accounts.models import Account
from ledger.models import Trx, Wallet
from ledger.utils.fields import get_amount_field, get_price_field, get_lock_field
from ledger.utils.precision import floor_precision, get_presentation_amount
from ledger.utils.price import get_trading_price_irt, IRT, USDT, get_trading_price_usdt
from market.models import PairSymbol
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class MarketOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(type=Order.ORDINARY)


class OpenOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.NEW)


class Order(models.Model):
    MIN_IRT_ORDER_SIZE = Decimal(1e5)
    MAKER_ORDERS_COUNT = 10 if settings.DEBUG else 50

    BUY, SELL = 'buy', 'sell'
    ORDER_CHOICES = [(BUY, BUY), (SELL, SELL)]

    LIMIT, MARKET = 'limit', 'market'
    FILL_TYPE_CHOICES = [(LIMIT, LIMIT), (MARKET, MARKET)]

    NEW, CANCELED, FILLED = 'new', 'canceled', 'filled'
    STATUS_CHOICES = [(NEW, NEW), (CANCELED, CANCELED), (FILLED, FILLED)]

    DEPTH = 'depth'
    ORDINARY = None

    TYPE_CHOICES = ((DEPTH, 'depth'), (ORDINARY, 'ordinary'))

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
    price = get_price_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)
    fill_type = models.CharField(max_length=8, choices=FILL_TYPE_CHOICES)
    status = models.CharField(default=NEW, max_length=8, choices=STATUS_CHOICES)

    lock = get_lock_field(null=True, related_name='market_order')

    client_order_id = models.CharField(max_length=36, null=True, blank=True)

    def __str__(self):
        return f'{self.symbol}-{self.side} [p:{self.price:.2f}] (a:{self.unfilled_amount:.5f}/{self.amount:.5f})'

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'type', 'status', 'created']),
        ]

    all_objects = models.Manager()
    objects = MarketOrderManager()
    open_objects = OpenOrderManager()

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(self.wallet.account, self.wallet.market)

    @property
    def filled_amount(self):
        amount = (self.made_fills.all().aggregate(sum=Sum('amount'))['sum'] or 0) + \
                 (self.taken_fills.all().aggregate(sum=Sum('amount'))['sum'] or 0)
        return floor_precision(Decimal(amount), self.symbol.step_size)

    @property
    def filled_price(self):
        made_fills_amount, made_fills_value = self.made_fills.all().annotate(
            value=F('amount') * F('price')).aggregate(sum_amount=Sum('amount'), sum_value=Sum('value')).values()
        taken_fills_amount, taken_fills_value = self.taken_fills.all().annotate(
            value=F('amount') * F('price')).aggregate(sum_amount=Sum('amount'), sum_value=Sum('value')).values()
        amount = Decimal((made_fills_amount or 0) + (taken_fills_amount or 0))
        if not amount:
            return None
        price = Decimal((made_fills_value or 0) + (taken_fills_value or 0)) / amount
        return floor_precision(price, self.symbol.tick_size)

    @property
    def unfilled_amount(self):
        amount = self.amount - self.filled_amount
        return floor_precision(amount, self.symbol.step_size)

    @staticmethod
    def get_opposite_side(side):
        return Order.SELL if side == Order.BUY else Order.BUY

    @staticmethod
    def get_order_by(side):
        return ('-price', '-created') if side == Order.BUY else ('price', '-created')

    @staticmethod
    def cancel_orders(symbol: PairSymbol, to_cancel_orders=None):
        if to_cancel_orders is None:
            to_cancel_orders = Order.open_objects.select_for_update().filter(
                symbol=symbol, cancel_request__isnull=False
            )
        for order in to_cancel_orders:
            order.release_lock()

        return to_cancel_orders.update(status=Order.CANCELED)

    @staticmethod
    def get_price_filter(price, side):
        return {'price__lte': price} if side == Order.BUY else {'price__gte': price}

    @staticmethod
    def get_maker_price(symbol: PairSymbol, side: str, loose_factor=Decimal(1)):
        coin = symbol.asset.symbol
        base_symbol = symbol.base_asset.symbol
        if base_symbol == IRT:
            boundary_price = get_trading_price_irt(coin, side)
        elif base_symbol == USDT:
            boundary_price = get_trading_price_usdt(coin, side)
        else:
            raise NotImplementedError('Invalid trading symbol')
        return boundary_price * loose_factor if side == Order.BUY else boundary_price / loose_factor

    @classmethod
    def get_lock_wallet(cls, wallet, base_wallet, side):
        return base_wallet if side == Order.BUY else wallet

    @classmethod
    def get_lock_amount(cls, amount, price, side):
        return amount * price if side == Order.BUY else amount

    @classmethod
    def submit(cls, order: 'Order'):
        order.acquire_lock()
        order.make_match()

    def acquire_lock(self):
        lock_wallet = self.get_lock_wallet(self.wallet, self.base_wallet, self.side)
        lock_amount = Order.get_lock_amount(self.amount, self.price, self.side)
        self.lock = lock_wallet.lock_balance(lock_amount)
        self.save()

    def release_lock(self, release_amount=None):
        if release_amount is None:
            self.lock.release()
            return

        from ledger.models import BalanceLock
        release_amount = Order.get_lock_amount(release_amount, self.price, self.side)
        BalanceLock.objects.filter(id=self.lock.id).update(amount=F('amount') - release_amount)

    def make_match(self):
        with transaction.atomic():
            from market.models import FillOrder

            cancels = self.cancel_orders(self.symbol)
            logger.info(f'cancels: {cancels}')

            opp_side = self.get_opposite_side(self.side)

            matching_orders = Order.open_objects.select_for_update().filter(
                symbol=self.symbol, side=opp_side, **Order.get_price_filter(self.price, self.side)
            ).order_by(*self.get_order_by(opp_side))
            logger.info(f'open orders: {matching_orders}')

            system = Account.system()

            unfilled_amount = self.unfilled_amount

            fill_orders = []
            trx_list = []
            for matching_order in matching_orders:
                trade_price = matching_order.price
                if (self.side == Order.BUY and self.price < trade_price) or (
                        self.side == Order.SELL and self.price > trade_price
                ):
                    continue
                match_amount = min(matching_order.unfilled_amount, unfilled_amount)
                if match_amount <= 0:
                    continue

                fill_order = FillOrder(
                    symbol=self.symbol,
                    taker_order=self,
                    maker_order=matching_order,
                    amount=match_amount,
                    price=trade_price,
                    is_buyer_maker=(self.side == Order.SELL),
                )
                trx_list.extend(fill_order.init_trade_trxs(system))
                fill_order.calculate_amounts_from_trx()

                fill_orders.append(fill_order)

                self.release_lock(match_amount)
                matching_order.release_lock(match_amount)

                orders_types = {self.type, matching_order.type}
                if Order.ORDINARY in orders_types and len(orders_types) == 2 and not settings.DEBUG:
                    ordinary_order = self if self.type == Order.ORDINARY else matching_order
                    placed_hedge_order = ProviderOrder.try_hedge_for_new_order(
                        asset=self.wallet.asset,
                        side=ordinary_order.side,
                        amount=match_amount,
                        scope=ProviderOrder.TRADE
                    )
                    if not placed_hedge_order:
                        raise Exception('failed placing hedge order', self)

                unfilled_amount -= match_amount
                if match_amount == matching_order.unfilled_amount:
                    matching_order.lock.release()
                    matching_order.status = Order.FILLED
                    matching_order.save(update_fields=['status'])

                if unfilled_amount <= 0:
                    self.lock.release()
                    self.status = Order.FILLED
                    self.save(update_fields=['status'])
                    if unfilled_amount < 0:
                        logger.critical(f'order {self.symbol} filled more than unfilled amount', extra={
                            'order_id': self.id,
                            'unfilled_amount': unfilled_amount,
                        })
                    break

            Trx.objects.bulk_create(filter(bool, trx_list))
            FillOrder.objects.bulk_create(fill_orders)

    # OrderBook related methods
    @classmethod
    def get_formatted_orders(cls, open_orders, symbol: PairSymbol, order_type: str):
        filtered_orders = list(filter(lambda o: o['side'] == order_type, open_orders))
        # hedge_orders = cls.get_hedge_orders(symbol, order_type)
        aggregated_orders = cls.get_aggregated_orders(symbol, *filtered_orders)

        sort_func = (lambda o: -Decimal(o['price'])) if order_type == Order.BUY else (lambda o: Decimal(o['price']))

        return sorted(aggregated_orders, key=sort_func)

    @staticmethod
    def get_aggregated_orders(symbol: PairSymbol, *orders):
        key_func = (lambda o: o['price'])
        grouped_by_price = groupby(sorted(orders, key=key_func), key=key_func)
        return [{
            'price': price,
            'amount': get_presentation_amount(sum(map(lambda i: i['unfilled_amount'], price_orders)), symbol.step_size),
            'total': get_presentation_amount(
                sum(map(lambda i: i['unfilled_amount'] * price, price_orders)), symbol.tick_size)
        } for price, price_orders in grouped_by_price]

    @staticmethod
    def quantize_values(symbol: PairSymbol, open_orders):
        return [{
            'side': order['side'],
            'price': get_presentation_amount(order['price'], symbol.tick_size),
            'unfilled_amount': floor_precision(order['unfilled_amount'], symbol.step_size),
        } for order in open_orders]

    # Market Maker related methods
    @staticmethod
    def init_maker_order(symbol: PairSymbol, side, maker_price: Decimal, system=None, market=Wallet.SPOT):
        if system is None:
            system = Account.system()

        amount = floor_precision(symbol.maker_amount * Decimal(1 + random()), symbol.step_size)
        wallet = symbol.asset.get_wallet(system, market=market)
        return Order(
            type=Order.DEPTH,
            wallet=wallet,
            symbol=symbol,
            amount=amount,
            price=floor_precision(maker_price, symbol.tick_size),
            side=side,
            fill_type=Order.LIMIT
        )

    @classmethod
    def init_top_maker_order(cls, symbol, side, price, best_order, best_opp_order, market=Wallet.SPOT,
                             system=None):
        if system is None:
            system = Account.system()

        maker_price = None
        if not best_opp_order:
            maker_price = price
        elif side == Order.BUY:
            maker_price = min(price, best_opp_order * Decimal(1 - 0.01))
        elif side == Order.SELL:
            maker_price = max(price, best_opp_order * Decimal(1 + 0.01))

        if not maker_price:
            logger.warning(f'cannot calculate maker price for {symbol} {side}')
            return

        loose_factor = Decimal('1.0005') if side == Order.BUY else 1 / Decimal('1.0005')
        if not best_order or \
                (side == Order.BUY and maker_price > best_order * loose_factor) or \
                (side == Order.SELL and maker_price < best_order * loose_factor):
            return cls.init_maker_order(symbol, side, maker_price, system, market)

    @classmethod
    def cancel_invalid_maker_orders(cls, symbol: PairSymbol):
        for side in (Order.BUY, Order.SELL):
            price = cls.get_maker_price(symbol, side, loose_factor=Decimal('1.0005'))
            invalid_orders = cls.open_objects.select_for_update().filter(symbol=symbol, side=side).exclude(
                type=Order.ORDINARY
            ).exclude(**cls.get_price_filter(price, side))
            cancels = cls.cancel_orders(symbol, to_cancel_orders=invalid_orders)
            logger.info(f'maker {side} cancels: {cancels}, price: {price}')
