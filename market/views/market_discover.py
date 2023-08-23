from rest_framework.views import APIView
from rest_framework.response import Response

from market.utils.trade import get_markets_info

from ledger.models import Asset


class MarketDiscoverView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        markets_info = {
            'USDT': get_markets_info(Asset.USDT),
            'IRT': get_markets_info(Asset.IRT)
        }
        return Response(markets_info)
