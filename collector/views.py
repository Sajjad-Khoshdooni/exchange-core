from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.authentication import TokenAuthentication

from ledger.utils.price import get_trading_price_usdt, get_trading_price_irt


class CoinPriceView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request, coin, side, base):
        if base == 'usdt':
            res = get_trading_price_usdt(coin=coin, side=side)
        elif base == 'irt':
            res = get_trading_price_irt(coin=coin, side=side)
        else:
            return Response(404)
        return Response({
            'price': res
        }, 200)


