import logging
from decimal import Decimal

from django.db.models import Sum, F, Subquery, OuterRef
from django.db.models.functions import Coalesce
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.precision import floor_precision
from accounts.throttle import BursApiRateThrottle
from market.models import PairSymbol, Order, FillOrder

logger = logging.getLogger(__name__)


class OrderBookAPIView(APIView):
    permission_classes = ()
    throttle_classes = [BursApiRateThrottle]

    def get(self, request, symbol):
        symbol = get_object_or_404(PairSymbol, name=symbol.upper())
        if not symbol.enable:
            raise ValidationError(f'{symbol} is not enable')
        open_orders = Order.open_objects.filter(symbol=symbol).annotate(
            total_made=Subquery(
                FillOrder.objects.filter(maker_order_id=OuterRef('pk')).values('maker_order_id').annotate(
                    sum=Sum('amount')).values('sum')[:1]),
            total_taken=Subquery(
                FillOrder.objects.filter(taker_order_id=OuterRef('pk')).values('taker_order_id').annotate(
                    sum=Sum('amount')).values('sum')[:1]),
        ).annotate(
            unfilled_amount=F('amount') - Coalesce(F('total_made'), Decimal(0)) - Coalesce(F('total_taken'), Decimal(0))
        ).exclude(unfilled_amount=0).values('side', 'price', 'unfilled_amount')

        open_orders = Order.quantize_values(symbol, open_orders)

        bids = Order.get_formatted_orders(open_orders, symbol, Order.BUY)
        asks = Order.get_formatted_orders(open_orders, symbol, Order.SELL)

        top_ask = Decimal(asks[0]['price']) if asks else Decimal('inf')

        filtered_bids = list(filter(lambda o: Decimal(o['price']) < top_ask if asks else True, bids))

        if len(filtered_bids) < len(bids):
            logger.critical(f'There are unmatched orders in {symbol} order book', extra={
                'symbol': str(symbol),
                'bids': bids,
                'asks': asks,
            })

        last_trade = FillOrder.get_last(symbol=symbol)

        results = {
            'last_trade': last_trade.format_values() if last_trade else {'amount': None, 'price': None, 'total': None},
            'bids': filtered_bids[:20],
            'asks': asks[:20],
        }

        if not request.auth and request.user and not request.user.is_anonymous:
            open_orders = {
                (order['side'], str(floor_precision(order['price'], symbol.tick_size))): True for order in
                Order.open_objects.filter(
                    symbol=symbol, wallet__account=self.request.user.account
                ).values('side', 'price')
            }
            for side in (Order.BUY, Order.SELL):
                key = 'bids' if side == Order.BUY else 'asks'
                results[key] = [
                    {**order, 'user_order': open_orders.get((side, order['price']), False)} for order in results[key]
                ]
        return Response(results, status=status.HTTP_200_OK)
