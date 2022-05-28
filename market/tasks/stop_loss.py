import logging

from celery import shared_task

from market.models import Order, PairSymbol
from market.models.stop_loss import StopLoss
from market.utils import new_order
from market.utils.order_utils import get_market_top_prices
from market.utils.redis import set_top_prices

logger = logging.getLogger(__name__)


@shared_task(queue='stop_loss')
def handle_stop_loss():
    stop_loss_symbols = list(StopLoss.open_objects.values_list('symbol__id', flat=True).distinct())
    market_top_prices = get_market_top_prices(stop_loss_symbols)

    for symbol_id in stop_loss_symbols:
        symbol_top_prices = {
            Order.BUY: market_top_prices[symbol_id, Order.BUY],
            Order.SELL: market_top_prices[symbol_id, Order.SELL],
        }
        set_top_prices(symbol_id, symbol_top_prices)
        for side in (Order.BUY, Order.SELL):
            create_needed_stop_loss_orders.apply_async(args=(symbol_id, side,), queue='stop_loss')


@shared_task(queue='stop_loss')
def create_needed_stop_loss_orders(symbol_id, side):
    market_top_prices = Order.get_top_prices(symbol_id)
    symbol_price = market_top_prices[side]
    stop_loss_qs = StopLoss.open_objects.filter(symbol_id=symbol_id).prefetch_related('wallet__account')
    if side == StopLoss.BUY:
        stop_loss_qs = stop_loss_qs.filter(price__lte=symbol_price)
    else:
        stop_loss_qs = stop_loss_qs.filter(price__gte=symbol_price)

    for stop_loss in stop_loss_qs:
        order = new_order(
            stop_loss.symbol, stop_loss.wallet.account, stop_loss.unfilled_amount, None, stop_loss.side, Order.MARKET,
            raise_exception=False
        )
        if not order:
            logger.warning(f'could not place market order for stop loss ({stop_loss.symbol})',
                           extra={'stop_loss': stop_loss.id})
            continue
        order.refresh_from_db()
        order.stop_loss = stop_loss
        order.save(update_fields=['stop_loss_id'])
        stop_loss.filled_amount += order.filled_amount
        stop_loss.save(update_fields=['filled_amount'])
        logger.info(f'filled order with amount: {order.filled_amount}, price: {order.price} for '
                    f'stop loss({stop_loss.id}) {stop_loss.filled_amount} {stop_loss.price} {stop_loss.side} ')
