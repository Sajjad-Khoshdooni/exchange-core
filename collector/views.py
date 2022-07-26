from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.views.authentication import CustomTokenAuthentication
from ledger.utils.price import get_trading_price_usdt, get_trading_price_irt


class CoinPriceView(APIView):
    authentication_classes = [CustomTokenAuthentication]

    def get(self, request):
        coin = request.GET['coin']
        side = request.GET['side']
        base = request.GET['base']
        if base == 'usdt':
            price = get_trading_price_usdt(coin=coin, side=side)
        elif base == 'irt':
            price = get_trading_price_irt(coin=coin, side=side)
        else:
            return Response(404)

        print(coin, side, base, price)
        return Response({
            'price': price
        }, 200)
