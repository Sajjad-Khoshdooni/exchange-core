import logging
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from market.models import PairSymbol, FillOrder
from market.serializers.tradingview_serializers import OHLCVSerializer

logger = logging.getLogger(__name__)


class OHLCVAPIView(APIView):
    permission_classes = ()

    def get(self, request, symbol):
        symbol = get_object_or_404(PairSymbol, name=symbol.upper())
        if not symbol.enable:
            raise ValidationError(f'{symbol} is not enable')
        candles = FillOrder.get_grouped_by_interval(
            symbol_id=symbol.id,
            interval_in_secs=request.query_params.get('interval', 3600),
            start=request.query_params.get('start', timezone.now() - timedelta(hours=24)),
            end=request.query_params.get('end', timezone.now())
        )
        results = OHLCVSerializer(data=candles, many=True, context={'symbol': symbol}).initial_data
        return Response(results, status=status.HTTP_200_OK)
