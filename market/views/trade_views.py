import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from market.models import Trade
from market.serializers.trade_serializer import TradeSerializer, AccountTradeSerializer


class TradeFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', required=True, lookup_expr='iexact')

    class Meta:
        model = Trade
        fields = ('symbol',)


class AccountTradeHistoryView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        market = self.request.query_params.get('market')
        if not market:
            return Trade.objects.filter(
                account=self.request.user.account
            ).select_related('symbol', 'symbol__asset', 'symbol__base_asset', 'order__wallet').order_by('-created')

        return Trade.objects.filter(
            account=self.request.user.account, maker_order__wallet__market=market
        ).select_related('symbol', 'symbol__asset', 'symbol__base_asset', 'order__wallet').order_by('-created')

    def get_serializer_context(self):
        return {
            **super(AccountTradeHistoryView, self).get_serializer_context(),
            'account': self.request.user.account
        }

    def list(self, request: Request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        result = []
        for index, trade in enumerate(page):
            result.append(AccountTradeSerializer(
                instance=trade,
                context={'account': self.request.user.account, 'index': index}
            ).data)

        return self.get_paginated_response(result)


class TradeHistoryView(ListAPIView):
    authentication_classes = ()
    permission_classes = ()
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]
    queryset = Trade.objects.exclude(trade_source=Trade.OTC).order_by('-created')
    serializer_class = TradeSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = TradeFilter
