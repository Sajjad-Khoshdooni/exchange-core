import logging
from collections import defaultdict
from decimal import Decimal
from math import log10

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Min, Count

from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import Order, PairSymbol
from market.utils.order_utils import get_market_top_prices
from market.utils.redis import set_top_prices, set_open_orders_count, get_open_orders_count, set_top_depth_prices, \
    get_top_depth_prices

logger = logging.getLogger(__name__)


@shared_task(queue='market')
def update_maker_orders():
    market_top_prices = get_market_top_prices()
    top_depth_prices = defaultdict(lambda: Decimal())

    depth_orders = Order.open_objects.filter(type__in=(Order.DEPTH, Order.BOT)).values('symbol', 'side').annotate(
        max_price=Max('price'),
        min_price=Min('price'),
        count=Count('*'))
    for depth in depth_orders:
        top_depth_prices[
            (depth['symbol'], depth['side'])
        ] = (depth['max_price'] if depth['side'] == Order.BUY else depth['min_price']) or Decimal()

    open_depth_orders_count = defaultdict(int)
    for depth in depth_orders:
        open_depth_orders_count[(depth['symbol'], depth['side'])] = depth['count'] or 0

    for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True, asset__enable=True):
        symbol_top_prices = {
            Order.BUY: market_top_prices[symbol.id, Order.BUY],
            Order.SELL: market_top_prices[symbol.id, Order.SELL],
        }
        set_top_prices(symbol.id, symbol_top_prices)
        symbol_top_depth_prices = {
            Order.BUY: top_depth_prices[symbol.id, Order.BUY],
            Order.SELL: top_depth_prices[symbol.id, Order.SELL],
        }
        set_top_depth_prices(symbol.id, symbol_top_depth_prices)
        symbol_open_depth_orders_count = {
            Order.BUY: open_depth_orders_count[symbol.id, Order.BUY],
            Order.SELL: open_depth_orders_count[symbol.id, Order.SELL],
        }
        set_open_orders_count(symbol.id, symbol_open_depth_orders_count)

        update_symbol_maker_orders.apply_async(
            args=(PairSymbol.IdName(id=symbol.id, name=symbol.name, tick_size=symbol.tick_size),), queue='market'
        )


@shared_task(queue='market')
def update_symbol_maker_orders(symbol):
    symbol = PairSymbol.IdName(*symbol)
    market_top_prices = Order.get_top_prices(symbol.id)
    top_depth_prices = get_top_depth_prices(symbol.id)
    open_depth_orders_count = get_open_orders_count(symbol.id)

    depth_orders = Order.open_objects.filter(
        symbol_id=symbol.id, type__in=(Order.DEPTH, Order.BOT)
    ).values('side').annotate(
        max_price=Max('price'), min_price=Min('price'), count=Count('*')
    )
    if not top_depth_prices:
        top_depth_prices = defaultdict(lambda: Decimal())
        for depth in depth_orders:
            top_depth_prices[depth['side']] = (depth['max_price'] if depth['side'] == Order.BUY else depth[
                'min_price']) or Decimal()

    if not open_depth_orders_count:
        open_depth_orders_count = defaultdict(lambda: Decimal())
        for depth in depth_orders:
            open_depth_orders_count[depth['side']] = depth['count'] or 0

    try:
        with transaction.atomic():
            Order.cancel_invalid_maker_orders(symbol, top_depth_prices)
            Order.cancel_invalid_maker_orders(symbol, top_depth_prices, gap=Decimal('0.001'), order_type=Order.BOT)

        for side in (Order.BUY, Order.SELL):
            logger.info(f'{symbol.name} {side} open count: {open_depth_orders_count[side]}')
            price = Order.get_maker_price(symbol, side)
            order = Order.init_top_maker_order(symbol, side, price, Decimal(market_top_prices[side]))
            logger.info(f'{symbol.name} {side} maker order created: {bool(order)}')
            if order:
                if int(open_depth_orders_count[side]) > Order.MAKER_ORDERS_COUNT:
                    with transaction.atomic():
                        Order.cancel_waste_maker_orders(symbol, open_depth_orders_count)
                with WalletPipeline() as pipeline:
                    order.save()
                    order.submit(pipeline)
    except Exception as e:
        if settings.DEBUG:
            raise e
        logger.exception(f'update maker order failed for {symbol}', extra={'exp': e, })


@shared_task(queue='market')
def create_depth_orders(symbol=None, open_depth_orders_count=None):
    def get_price_factor(order_side, distance):
        factor = Decimal(1 + (log10(11 + distance) - 1) / 4)
        return factor if order_side == Order.SELL else 1 / factor

    if open_depth_orders_count is None:
        open_depth_orders_count = defaultdict(int)
        for depth in Order.open_objects.filter(type=Order.DEPTH).values('symbol', 'side').annotate(count=Count('*')):
            open_depth_orders_count[(depth['symbol'], depth['side'])] = depth['count'] or 0

    if symbol is None:
        for symbol in PairSymbol.objects.filter(market_maker_enabled=True, enable=True, asset__enable=True):
            symbol_open_depth_orders_count = {
                Order.BUY: open_depth_orders_count[symbol.id, Order.BUY],
                Order.SELL: open_depth_orders_count[symbol.id, Order.SELL],
            }
            pair_symbol = PairSymbol.IdName(id=symbol.id, name=symbol.name, tick_size=symbol.tick_size)
            create_depth_orders.apply_async(args=(pair_symbol, symbol_open_depth_orders_count), queue='market')
    else:
        symbol = PairSymbol.IdName(*symbol)
        present_prices = set(
            Order.open_objects.filter(symbol_id=symbol.id, type=Order.DEPTH).values_list('price', flat=True))
        try:
            for side in (Order.BUY, Order.SELL):
                price = Order.get_maker_price(symbol, side)
                for rank in range(open_depth_orders_count[side], Order.MAKER_ORDERS_COUNT):
                    order = Order.init_maker_order(symbol, side, price * get_price_factor(side, rank))
                    if order and order.price not in present_prices:
                        with WalletPipeline() as pipeline:
                            order.save()
                            order.submit(pipeline)
        except Exception as e:
            if settings.DEBUG:
                raise e
            logger.exception(f'create depth order failed for {symbol.name}', extra={'exp': e, })
