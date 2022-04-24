import logging
from collections import defaultdict
from decimal import Decimal
from math import log10

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Min, Count

from accounts.models import Account
from market.models import Order, PairSymbol

logger = logging.getLogger(__name__)


@shared_task(queue='market')
def update_maker_orders(symbol_id=None, market_top_prices=None, open_depth_orders_count=None):
    if market_top_prices is None:
        market_top_prices = defaultdict(lambda: Decimal())

        for depth in Order.open_objects.values('symbol', 'side').annotate(
                max_price=Max('price'), min_price=Min('price')):
            market_top_prices[
                (depth['symbol'], depth['side'])
            ] = (depth['max_price'] if depth['side'] == Order.BUY else depth['min_price']) or Decimal()

    if open_depth_orders_count is None:
        open_depth_orders_count = defaultdict(int)
        for depth in Order.open_objects.filter(type=Order.DEPTH).values('symbol', 'side').annotate(count=Count('*')):
            open_depth_orders_count[(depth['symbol'], depth['side'])] = depth['count'] or 0

    if symbol_id is None:
        for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True):
            symbol_top_prices = {
                Order.BUY: market_top_prices[symbol.id, Order.BUY],
                Order.SELL: market_top_prices[symbol.id, Order.SELL],
            }
            symbol_open_depth_orders_count = {
                Order.BUY: open_depth_orders_count[symbol.id, Order.BUY],
                Order.SELL: open_depth_orders_count[symbol.id, Order.SELL],
            }
            update_maker_orders.apply_async(
                args=(symbol.id, symbol_top_prices, symbol_open_depth_orders_count), queue='market'
            )
    else:
        symbol = PairSymbol.objects.get(id=symbol_id)
        try:
            with transaction.atomic():
                Order.cancel_invalid_maker_orders(symbol)

            for side in (Order.BUY, Order.SELL):
                logger.info(f'{symbol} {side} open count: {open_depth_orders_count[side]}')
                if open_depth_orders_count[side] > Order.MAKER_ORDERS_COUNT:
                    with transaction.atomic():
                        Order.cancel_waste_maker_orders(symbol, open_depth_orders_count)
                price = Order.get_maker_price(symbol, side)
                order = Order.init_top_maker_order(
                    symbol, side, price,
                    Decimal(market_top_prices[side]), Decimal(market_top_prices[Order.get_opposite_side(side)])
                )
                logger.info(f'{symbol} {side} maker order created: {bool(order)}')
                if order:
                    with transaction.atomic():
                        order.save()
                        order.submit()
        except Exception as e:
            if settings.DEBUG:
                raise e
            logger.exception(f'update maker order failed for {symbol}', extra={'exp': e, })


@shared_task(queue='market')
def create_depth_orders(symbol_id=None, open_depth_orders_count=None):
    def get_price_factor(order_side, distance):
        factor = Decimal(1 + (log10(11 + distance) - 1) / 4)
        return factor if order_side == Order.SELL else 1 / factor

    if open_depth_orders_count is None:
        open_depth_orders_count = defaultdict(int)
        for depth in Order.open_objects.filter(type=Order.DEPTH).values('symbol', 'side').annotate(count=Count('*')):
            open_depth_orders_count[(depth['symbol'], depth['side'])] = depth['count'] or 0

    if symbol_id is None:
        for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True):
            symbol_open_depth_orders_count = {
                Order.BUY: open_depth_orders_count[symbol.id, Order.BUY],
                Order.SELL: open_depth_orders_count[symbol.id, Order.SELL],
            }
            create_depth_orders.apply_async(args=(symbol.id, symbol_open_depth_orders_count), queue='market')
    else:
        symbol = PairSymbol.objects.get(id=symbol_id)
        system = Account.system()
        present_prices = set(Order.open_objects.filter(symbol=symbol, type=Order.DEPTH).values_list('price', flat=True))
        try:
            for side in (Order.BUY, Order.SELL):
                price = Order.get_maker_price(symbol, side)
                for i in range(Order.MAKER_ORDERS_COUNT - open_depth_orders_count[side]):
                    order = Order.init_maker_order(symbol, side, price * get_price_factor(side, i), system)
                    if order and order.price not in present_prices:
                        with transaction.atomic():
                            order.save()
                            order.submit()
        except Exception as e:
            if settings.DEBUG:
                raise e
            logger.exception(f'create depth order failed for {symbol}', extra={'exp': e, })
