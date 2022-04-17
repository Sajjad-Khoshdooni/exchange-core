import logging
from datetime import timedelta, datetime
from decimal import Decimal

import pytz
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.precision import floor_precision
from market.models import PairSymbol, FillOrder

logger = logging.getLogger(__name__)


class OHLCVSerializer:
    def __init__(self, candles, symbol):
        self.candles = candles
        self.symbol = symbol

    def format_data(self):
        return [self.format_single_obj(obj) for obj in self.candles]

    @staticmethod
    def get_timestamp(obj):
        return obj['timestamp'].timestamp()

    def get_open(self, obj):
        return self.format_price(self.symbol, obj['open'])

    def get_high(self, obj):
        return self.format_price(self.symbol, obj['high'])

    def get_low(self, obj):
        return self.format_price(self.symbol, obj['low'])

    def get_close(self, obj):
        return self.format_price(self.symbol, obj['close'])

    def get_volume(self, obj):
        return floor_precision(obj['volume'], self.symbol.step_size)

    @staticmethod
    def format_price(symbol: PairSymbol, price: Decimal):
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
    permission_classes = ()

    def get(self, request):
        symbol = request.query_params.get('symbol')
        if not symbol:
            raise ValidationError(f'symbol is required')
        symbol = get_object_or_404(PairSymbol, name=symbol.upper())
        if not symbol.enable:
            raise ValidationError(f'{symbol} is not enable')
        start = request.query_params.get('from', (timezone.now() - timedelta(hours=24)).timestamp())
        end = request.query_params.get('to', timezone.now().timestamp())
        candles = FillOrder.get_grouped_by_interval(
            symbol_id=symbol.id,
            interval_in_secs=request.query_params.get('resolution', 3600),
            start=datetime.fromtimestamp(int(start), tz=pytz.UTC),
            end=datetime.fromtimestamp(int(end), tz=pytz.UTC)
        )
        results = OHLCVSerializer(candles=candles, symbol=symbol).format_data()
        return Response(results, status=status.HTTP_200_OK)
