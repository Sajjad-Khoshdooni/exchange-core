import django_filters
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from market.models import FillOrder
from market.serializers.trade_serializer import FillOrderSerializer, TradeSerializer


class TradeFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', required=True, lookup_expr='iexact')

    class Meta:
        model = FillOrder
        fields = ('symbol',)


class AccountTradeHistoryView(ListAPIView):
    authentication_classes = (SessionAuthentication,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        market = self.request.query_params.get('market')
        if not market:
            return FillOrder.objects.filter(
                Q(maker_order__wallet__account=self.request.user.account) |
                Q(taker_order__wallet__account=self.request.user.account)
            ).select_related(
                'maker_order__wallet__account', 'taker_order__wallet__account', 'symbol__asset', 'symbol__base_asset'
            ).order_by('-created')

        return FillOrder.objects.filter(
                Q(maker_order__wallet__account=self.request.user.account, maker_order__wallet__market=market) |
                Q(taker_order__wallet__account=self.request.user.account, taker_order__wallet__market=market)
            ).select_related(
                'maker_order__wallet__account', 'taker_order__wallet__account', 'symbol__asset', 'symbol__base_asset'
            ).order_by('-created')

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
            result.append(FillOrderSerializer(
                instance=trade,
                context={'account': self.request.user.account, 'index': index}
            ).data)

        return self.get_paginated_response(result)


class TradeHistoryView(ListAPIView):
    authentication_classes = ()
    permission_classes = ()
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]
    queryset = FillOrder.objects.exclude(trade_source=FillOrder.OTC).order_by('-created')
    serializer_class = TradeSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = TradeFilter
