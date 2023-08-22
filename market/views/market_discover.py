from rest_framework.views import APIView
from rest_framework.response import Response

from market.utils.price import get_symbol_prices
from market.models import PairSymbol
from market.utils.trade import get_market_size_ratio


class MarketDiscoverView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        prices = get_symbol_prices()
        recent_prices = prices['last']
        yesterday_prices = prices['yesterday']

        change_percents = {
            PairSymbol.objects.get(pair_symbol_id).asset.symbol:
                100 * (recent_prices[pair_symbol_id] - yesterday_prices[pair_symbol_id]) //
                yesterday_prices[pair_symbol_id]
            for pair_symbol_id in recent_prices.keys() & yesterday_prices.keys()
            if recent_prices[pair_symbol_id] and yesterday_prices[pair_symbol_id]
        }

        market_ratios = get_market_size_ratio()

        market_details = {
            pair_symbol.name: [ratio, change_percents.get(pair_symbol.asset.symbol, 0)]
            for pair_symbol, ratio in market_ratios
            if pair_symbol and ratio and change_percents.get('symbol')
        }

        return Response(market_details)
