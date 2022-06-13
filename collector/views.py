from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.authentication import TokenAuthentication

from ledger.utils.price import get_trading_price_usdt


class PriceGetterSerializer(serializers.Serializer):
    coin = serializers.CharField(max_length=16)
    side = serializers.CharField(max_length=16)
    raw_price = serializers.BooleanField(default=True)


class PriceGetterView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        serializer = PriceGetterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.data
        res = get_trading_price_usdt(data['coin'], side=data['side'], raw_price=data['raw_price'])
        return Response(res, 201)


