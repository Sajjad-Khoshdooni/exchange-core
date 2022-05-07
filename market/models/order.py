import logging
from decimal import Decimal
from itertools import groupby
from math import floor, log10
from random import randrange

from django.conf import settings
from django.db import models, transaction
from django.db.models import Sum, F, Q
from django.utils import timezone

from ledger.models import Trx, Wallet, BalanceLock
from ledger.models.asset import Asset
from ledger.utils.fields import get_amount_field, get_price_field, get_lock_field
from ledger.utils.precision import floor_precision, round_down_to_exponent
from ledger.utils.price import get_trading_price_irt, IRT, USDT, get_trading_price_usdt, get_tether_irt_price
from market.models import PairSymbol
from market.models.referral_trx import ReferralTrx
from provider.models import ProviderOrder

logger = logging.getLogger(__name__)


class OpenOrderManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Order.NEW)


class Order(models.Model):
    MIN_IRT_ORDER_SIZE = Decimal(1e5)
    MIN_USDT_ORDER_SIZE = Decimal(5)
    MAX_ORDER_DEPTH_SIZE_IRT = Decimal(5e7)
    MAX_ORDER_DEPTH_SIZE_USDT = Decimal(2000)
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
    filled_amount = get_amount_field(default=Decimal(0))
    price = get_price_field()
    side = models.CharField(max_length=8, choices=ORDER_CHOICES)
    fill_type = models.CharField(max_length=8, choices=FILL_TYPE_CHOICES)
    status = models.CharField(default=NEW, max_length=8, choices=STATUS_CHOICES)

    lock = get_lock_field(related_name='market_order')

    client_order_id = models.CharField(max_length=36, null=True, blank=True)

    def __str__(self):
        return f'({self.id}) {self.symbol}-{self.side} [p:{self.price:.2f}] (a:{self.unfilled_amount:.5f}/{self.amount:.5f})'

    class Meta:
        indexes = [
            models.Index(fields=['symbol', 'type', 'status', 'created']),
            models.Index(fields=['symbol', 'status']),
            models.Index(name='market_new_orders_price_idx', fields=['price'], condition=Q(status='new')),
        ]

    objects = models.Manager()
    open_objects = OpenOrderManager()

    @property
    def base_wallet(self):
        return self.symbol.base_asset.get_wallet(self.wallet.account, self.wallet.market)

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

    @classmethod
    def cancel_orders(cls, to_cancel_orders):
        to_cancel_orders = to_cancel_orders.exclude(status=cls.FILLED)

        now = timezone.now()

        lock_ids = list(to_cancel_orders.values_list('lock_id', flat=True))
        cancels = to_cancel_orders.update(status=Order.CANCELED)

        BalanceLock.objects.filter(id__in=lock_ids).update(freed=True, release_date=now)

        logger.info(f'cancels: {cancels}')

    @staticmethod
    def get_price_filter(price, side):
        return {'price__lte': price} if side == Order.BUY else {'price__gte': price}

    @staticmethod
    def get_maker_price(symbol: PairSymbol.IdName, side: str, loose_factor=Decimal(1)):
        if symbol.name.endswith(IRT):
            base_symbol = IRT
            get_trading_price = get_trading_price_irt
        elif symbol.name.endswith(USDT):
            base_symbol = USDT
            get_trading_price = get_trading_price_usdt
        else:
            raise NotImplementedError('Invalid trading symbol')

        coin = symbol.name.split(base_symbol)[0]
        boundary_price = get_trading_price(coin, side)

        return boundary_price * loose_factor if side == Order.BUY else boundary_price / loose_factor

    @classmethod
    def get_lock_wallet(cls, wallet, base_wallet, side):
        return base_wallet if side == Order.BUY else wallet

    @classmethod
    def get_lock_amount(cls, amount, price, side):
        return amount * price if side == Order.BUY else amount

    def submit(self):
        self.acquire_lock()
        self.make_match()

    def acquire_lock(self):
        lock_wallet = self.get_lock_wallet(self.wallet, self.base_wallet, self.side)
        lock_amount = Order.get_lock_amount(self.amount, self.price, self.side)
        self.lock = lock_wallet.lock_balance(lock_amount)
        self.save()

    def release_lock(self, release_amount):
        from ledger.models import BalanceLock
        release_amount = Order.get_lock_amount(release_amount, self.price, self.side)
        BalanceLock.objects.filter(id=self.lock.id).update(amount=F('amount') - release_amount)

    def make_match(self):
        with transaction.atomic():
            from market.models import FillOrder
            # lock current order
            Order.objects.select_for_update().filter(id=self.id).first()

            to_cancel_orders = Order.open_objects.filter(
                symbol=self.symbol, cancel_request__isnull=False
            )
            self.cancel_orders(to_cancel_orders)

            opp_side = self.get_opposite_side(self.side)

            matching_orders = Order.open_objects.select_for_update().filter(
                symbol=self.symbol, side=opp_side, **Order.get_price_filter(self.price, self.side)
            ).order_by(*self.get_order_by(opp_side))

            logger.info(f'open orders: {matching_orders}')

            unfilled_amount = self.unfilled_amount

            fill_orders = []
            trx_list = []

            referral_list = []
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

                is_system_trade = self.wallet.account.is_system() and matching_order.wallet.account.is_system()

                fill_order = FillOrder(
                    symbol=self.symbol,
                    taker_order=self,
                    maker_order=matching_order,
                    amount=match_amount,
                    price=trade_price,
                    is_buyer_maker=(self.side == Order.SELL),
                    irt_value=base_irt_price * trade_price * match_amount,
                    trade_source=FillOrder.SYSTEM if is_system_trade else FillOrder.MARKET
                )
                trade_trx_list = fill_order.init_trade_trxs()
                trx_list.extend(trade_trx_list.values())
                fill_order.calculate_amounts_from_trx(trade_trx_list)
                referral_trx = fill_order.init_referrals(trade_trx_list)
                trx_list.extend(referral_trx.trx)
                referral_list.extend(referral_trx.referral)

                fill_orders.append(fill_order)

                self.release_lock(match_amount)
                matching_order.release_lock(match_amount)
                self.update_filled_amount((self.id, matching_order.id), match_amount)

                if self.wallet.account.is_ordinary_user() != matching_order.wallet.account.is_ordinary_user():
                    ordinary_order = self if self.type == Order.ORDINARY else matching_order
                    placed_hedge_order = ProviderOrder.try_hedge_for_new_order(
                        asset=self.wallet.asset,
                        side=ordinary_order.side,
                        amount=match_amount,
                        scope=ProviderOrder.TRADE
                    )

                    if not placed_hedge_order:
                        logger.exception(
                            'failed placing hedge order',
                            extra={
                                'order': ordinary_order
                            }
                        )

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

            Trx.objects.bulk_create(filter(lambda trx: trx and trx.amount, trx_list))
            ReferralTrx.objects.bulk_create(filter(lambda referral: referral, referral_list))
            FillOrder.objects.bulk_create(fill_orders)

    # OrderBook related methods
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
        maker_amount = symbol_instance.maker_amount * Decimal(randrange(1, 40) / 20.0)
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
    def init_top_maker_order(cls, symbol, side, price, best_order, best_opp_order, market=Wallet.SPOT):
        maker_price = None
        if not best_opp_order:
            maker_price = price
        elif side == Order.BUY:
            maker_price = min(price, best_opp_order * Decimal(1 - 0.01))
        elif side == Order.SELL:
            maker_price = max(price, best_opp_order * Decimal(1 + 0.01))

        if not maker_price:
            logger.warning(f'cannot calculate maker price for {symbol.name} {side}')
            return
        symbol_instance = PairSymbol.objects.get(id=symbol.id)
        precision = Order.get_rounding_precision(maker_price, symbol_instance.tick_size)
        maker_price = round_down_to_exponent(maker_price, precision)

        loose_factor = Decimal('1.001') if side == Order.BUY else 1 / Decimal('1.001')
        if not best_order or \
                (side == Order.BUY and maker_price > best_order * loose_factor) or \
                (side == Order.SELL and maker_price < best_order * loose_factor):
            return cls.init_maker_order(symbol, side, maker_price, market)

    @classmethod
    def cancel_invalid_maker_orders(cls, symbol: PairSymbol.IdName, top_prices):
        for side in (Order.BUY, Order.SELL):
            price = cls.get_maker_price(symbol, side, loose_factor=Decimal('1.001'))
            if (side == Order.BUY and Decimal(top_prices[side]) <= price) or (
                    side == Order.SELL and Decimal(top_prices[side]) >= price):
                logger.info(f'maker {side} ignore cancels with price: {price} top: {top_prices[side]}')
                continue

            invalid_orders = Order.open_objects.select_for_update().filter(symbol_id=symbol.id, side=side).exclude(
                type=Order.ORDINARY
            ).exclude(**cls.get_price_filter(price, side))

            cls.cancel_orders(invalid_orders)

            logger.info(f'maker {side} cancels with price: {price}')

    @classmethod
    def cancel_waste_maker_orders(cls, symbol: PairSymbol.IdName, open_orders_count):
        for side in (Order.BUY, Order.SELL):
            wasted_orders = Order.open_objects.filter(symbol_id=symbol.id, side=side).exclude(
                type=Order.ORDINARY
            )
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
