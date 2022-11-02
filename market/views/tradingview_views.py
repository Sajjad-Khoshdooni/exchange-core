import logging
from datetime import timedelta, datetime
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.precision import floor_precision
from market.models import PairSymbol, Trade

logger = logging.getLogger(__name__)


class OHLCVSerializer:
    def __init__(self, candles, symbol):
        self.candles = candles
        self.symbol = symbol

    def format_data(self):
        return [self.format_single_obj(obj) for obj in self.candles]

    @staticmethod
    def get_timestamp(obj):
        return int(obj['timestamp'].timestamp() * 1000)

    def get_open(self, obj):
        return self.format_price(self.symbol, obj['open'])

    def get_high(self, obj):
        return self.format_price(self.symbol, obj['high'])

    def get_low(self, obj):
        return self.format_price(self.symbol, obj['low'])

    def get_close(self, obj):
        return self.format_price(self.symbol, obj['close'])

    def get_volume(self, obj):
        if obj['volume'] is None:
            return
        return floor_precision(obj['volume'], self.symbol.step_size)

    @staticmethod
    def format_price(symbol: PairSymbol, price: Decimal):
        if price is None:
            return
        return floor_precision(price, symbol.tick_size)

    def format_single_obj(self, obj):
        return {
            'time': self.get_timestamp(obj),
            'open': self.get_open(obj),
            'high': self.get_high(obj),
            'low': self.get_low(obj),
            'close': self.get_close(obj),
            'volume': self.get_volume(obj),
        }


class OHLCVAPIView(APIView):
    authentication_classes = ()
    permission_classes = ()

    @classmethod
    def append_empty_candles(cls, candles, interval):
        if not candles:
            return candles

        first_candle = candles[0]
        last_candle = candles[-1]
        candle_datetime = first_candle['timestamp']
        current_candle = first_candle
        included_timestamps = {candle['timestamp']: candle for candle in candles}
        position = 0
        while candle_datetime < last_candle['timestamp']:
            close = current_candle['close']
            candle_datetime += interval
            position += 1
            if candle_datetime in included_timestamps:
                current_candle = included_timestamps[candle_datetime]
                continue
            candles.insert(
                position, {
                    'timestamp': candle_datetime, 'open': close, 'high': close, 'low': close, 'close': close,
                    'volume': Decimal(0)
                }
            )
        return candles

    def get(self, request):
        symbol = request.query_params.get('symbol')
        if not symbol:
            raise ValidationError(f'symbol is required')
        symbol = get_object_or_404(PairSymbol, name=symbol.upper())
        if not symbol.enable:
            raise ValidationError(f'{symbol} is not enable')
        start = request.query_params.get('from', (timezone.now() - timedelta(hours=24)).timestamp())
        end = request.query_params.get('to', timezone.now().timestamp())
        interval = request.query_params.get('resolution', 3600)
        count_back = request.query_params.get('countBack', 0)
        candles = Trade.get_grouped_by_count(
            symbol_id=symbol.id,
            interval_in_secs=interval,
            start=datetime.fromtimestamp(int(start)).astimezone(),
            end=datetime.fromtimestamp(int(end)).astimezone(),
            count_back=int(count_back)
        )
        candles = self.append_empty_candles(candles, timedelta(seconds=int(interval)))
        results = OHLCVSerializer(candles=candles, symbol=symbol).format_data()
        return Response(results, status=status.HTTP_200_OK)
