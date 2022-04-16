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
def update_maker_orders():
    market_top_prices = defaultdict(lambda: Decimal())

    for depth in Order.open_objects.values('symbol', 'side').annotate(
            max_price=Max('price'), min_price=Min('price')):
        market_top_prices[
            (depth['symbol'], depth['side'])
        ] = (depth['max_price'] if depth['side'] == Order.BUY else depth['min_price']) or Decimal()

    for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True):
        try:
            with transaction.atomic():
                Order.cancel_invalid_maker_orders(symbol)

            for side in (Order.BUY, Order.SELL):
                price = Order.get_maker_price(symbol, side)
                order = Order.init_top_maker_order(
                    symbol, side, price,
                    market_top_prices[(symbol.id, side)], market_top_prices[(symbol.id, Order.get_opposite_side(side))]
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
def create_depth_orders():
    def get_price_factor(order_side, distance):
        factor = Decimal(1 + (log10(11 + distance) - 1) / 4)
        return factor if order_side == Order.SELL else 1 / factor

    open_depth_orders_count = defaultdict(int)
    for depth in Order.open_objects.filter(type=Order.DEPTH).values('symbol', 'side').annotate(count=Count('*')):
        open_depth_orders_count[(depth['symbol'], depth['side'])] = depth['count'] or 0

    system = Account.system()
    for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True):
        present_prices = set(Order.open_objects.filter(symbol=symbol, type=Order.DEPTH).values_list('price', flat=True))
        try:
            for side in (Order.BUY, Order.SELL):
                price = Order.get_maker_price(symbol, side)
                for i in range(Order.MAKER_ORDERS_COUNT - open_depth_orders_count[(symbol.id, side)]):
                    order = Order.init_maker_order(symbol, side, price * get_price_factor(side, i), system)
                    if order and order.price not in present_prices:
                        with transaction.atomic():
                            order.save()
                            order.submit()
        except Exception as e:
            if settings.DEBUG:
                raise e
            logger.exception(f'create depth order failed for {symbol}', extra={'exp': e, })
