from decimal import Decimal

import django_filters
from django.db.models import Min, Max
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.authentication import CustomTokenAuthentication
from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from ledger.models.wallet import ReserveWallet
from market.models import Trade, PairSymbol, Order
from market.pagination import FastLimitOffsetPagination
from market.serializers.trade_serializer import TradePairSerializer, TradeSerializer, AccountTradeSerializer


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
            account=self.request.user.get_account(),
            status=Trade.DONE,
        )

        if self.request.query_params.get('agent') and self.request.query_params.get('strategy'):
            reserve_wallet = ReserveWallet.objects.filter(
                request_id=f'strategy:{self.request.query_params.get("strategy")}:{self.request.query_params.get("agent")}'
            ).first()
            orders = set(Order.objects.filter(wallet__variant=reserve_wallet.group_id, filled_amount__gt=Decimal('0')).
                         values_list('id', flat=True))
            trades.filter(order_id__in=orders)

        market = self.request.query_params.get('market')
        if market:
            trades = trades.filter(market=market)

        return trades.select_related('symbol', 'symbol__asset', 'symbol__base_asset').order_by('-created')


class TradeHistoryView(ListAPIView):
    permission_classes = ()
    pagination_class = FastLimitOffsetPagination
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    def get_queryset(self):
        symbol = self.request.query_params.get('symbol')
        my = self.request.query_params.get('my')
        pair_symbol = get_object_or_404(PairSymbol, name=symbol)

        user = self.request.user

        if my == '1':
            if not user.is_authenticated:
                return Trade.objects.none()

            return Trade.objects.filter(
                account=user.get_account(),
                symbol=pair_symbol
            ).order_by('-created')[:15]

        else:
            return Trade.objects.filter(
                is_maker=True,
                symbol=pair_symbol
            ).order_by('-created')[:15]

    def list(self, request, *args, **kwargs):
        serializer = TradeSerializer(self.get_queryset(), many=True)

        return Response({
            'results': serializer.data
        })


class TradePairsHistoryView(ListAPIView):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    def get_queryset(self):
        min_id = self.request.query_params.get('from_id')
        id_filter = {'id__gt': min_id} if min_id else {}
        return Trade.objects.filter(
            account=self.request.user.account,
            **id_filter
        ).prefetch_related('symbol').order_by('id')

    def list(self, request, *args, **kwargs):
        min_id = self.request.query_params.get('from_id')
        id_filter = {'id__gt': min_id} if min_id else {}
        qs = self.get_queryset()
        maker_taker_mapping = {
            t['group_id']: (t['maker_order_id'], t['taker_order_id']) for t in
            Trade.objects.filter(group_id__in=qs.values_list('group_id', flat=True), **id_filter).values(
                'group_id').annotate(
                maker_order_id=Min('order_id'), taker_order_id=Max('order_id')
            )
        }
        all_order_ids = set(sum(maker_taker_mapping.values(), ()))
        client_order_id_mapping = {o.id: o.client_order_id for o in Order.objects.filter(id__in=all_order_ids)}
        serializer = TradePairSerializer(qs, context={
            'maker_taker_mapping': maker_taker_mapping,
            'client_order_id_mapping': client_order_id_mapping,
        }, many=True)

        return Response({
            'results': serializer.data
        })
