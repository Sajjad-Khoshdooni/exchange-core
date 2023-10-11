from rest_framework.response import Response
from rest_framework.views import APIView

from ledger.utils.external_price import fetch_external_price, SIDES


class HealthView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        return Response({'status': 'healthy!'})


class PriceHealthView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):

        symbols = ['BTCUSDT', 'ETHUSDT', 'DOGEUSDT', 'XCOINUSDT']

        missing_prices = []

        for s in symbols:
            for side in SIDES:
                if fetch_external_price(symbol=s, side=side, allow_stale=False) is None:
                    missing_prices.append(s)

        if not missing_prices:
            return Response({'status': 'healthy!'})
        else:
            return Response({'status': 'dead', 'symbols': missing_prices})
