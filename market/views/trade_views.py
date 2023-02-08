import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from market.models import Trade, PairSymbol, BaseTrade
from market.pagination import FastLimitOffsetPagination
from market.serializers.trade_serializer import TradeSerializer, AccountTradeSerializer


class TradeFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', required=True, lookup_expr='iexact')

    class Meta:
        model = Trade
        fields = ('symbol',)


class AccountTradeFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', lookup_expr='iexact')

    class Meta:
        model = Trade
        fields = ('symbol', 'side')


class AccountTradeHistoryView(ListAPIView):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    pagination_class = LimitOffsetPagination
    serializer_class = AccountTradeSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = AccountTradeFilter

    def get_queryset(self):
        trades = Trade.objects.filter(
            account=self.request.user.account,
            status=Trade.DONE,
        )

        market = self.request.query_params.get('market')
        if market:
            trades = trades.filter(market=market)

        return trades.select_related('symbol', 'symbol__asset', 'symbol__base_asset').order_by('-created')


class TradeHistoryView(ListAPIView):
    authentication_classes = ()
    permission_classes = ()
    pagination_class = FastLimitOffsetPagination
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    def get_queryset(self):
        symbol = self.request.query_params.get('symbol')
        pair_symbol = get_object_or_404(PairSymbol, name=symbol)

        return Trade.objects.filter(
            is_maker=True,
            symbol=pair_symbol
        ).exclude(trade_source=Trade.OTC).order_by('-created')[:15]

    def list(self, request, *args, **kwargs):
        serializer = TradeSerializer(self.get_queryset(), many=True)

        return Response({
            'results': serializer.data
        })
