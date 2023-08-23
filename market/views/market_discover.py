from rest_framework.views import APIView
from rest_framework.response import Response

from market.utils.price import get_symbol_prices
from market.models import PairSymbol
from market.utils.trade import get_market_size_ratio


class IRMarketDiscoverView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        prices = get_symbol_prices()
        recent_prices = prices['last']
        yesterday_prices = prices['yesterday']

        change_percents = {
            PairSymbol.objects.get(pair_symbol_id).name:
                100 * (recent_prices[pair_symbol_id] - yesterday_prices[pair_symbol_id]) //
                yesterday_prices[pair_symbol_id]
            for pair_symbol_id in recent_prices.keys() & yesterday_prices.keys()
            if recent_prices[pair_symbol_id] and yesterday_prices[pair_symbol_id]
        }

        market_ratios = get_market_size_ratio()

        market_details = {
            market: [ratio, change_percents.get(market, 0)]
            for market, ratio in market_ratios
            if market and ratio and change_percents.get(market)
        }

        return Response(market_details)

class USMarketDiscoverView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        prices = get_symbol_prices()
        recent_prices = prices['last']
        yesterday_prices = prices['yesterday']

        change_percents = {
            PairSymbol.objects.get(pair_symbol_id).name:
                100 * (recent_prices[pair_symbol_id] - yesterday_prices[pair_symbol_id]) //
                yesterday_prices[pair_symbol_id]
            for pair_symbol_id in recent_prices.keys() & yesterday_prices.keys()
            if recent_prices[pair_symbol_id] and yesterday_prices[pair_symbol_id]
        }

        market_ratios = get_market_size_ratio()

        market_details = {
            market: [ratio, change_percents.get(market, 0)]
            for market, ratio in market_ratios
            if market and ratio and change_percents.get(market)
        }

        return Response(market_details)
