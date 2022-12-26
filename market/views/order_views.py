from datetime import datetime

import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.throttle import BursAPIRateThrottle, SustainedAPIRateThrottle
from accounts.authentication import CustomTokenAuthentication
from accounts.views.jwt_views import DelegatedAccountMixin, user_has_delegate_permission
from ledger.models.wallet import ReserveWallet
from market.models import Order, CancelRequest
from market.models import StopLoss, Trade
from market.serializers.cancel_request_serializer import CancelRequestSerializer
from market.serializers.order_serializer import OrderSerializer
from market.serializers.order_stoploss_serializer import OrderStopLossSerializer
from market.serializers.stop_loss_serializer import StopLossSerializer


class OrderFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', lookup_expr='iexact')
    market = django_filters.CharFilter(field_name='wallet__market')

    class Meta:
        model = Order
        fields = ('symbol', 'status', 'market', 'side')


class StopLossFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name')
    market = django_filters.CharFilter(field_name='wallet__market')

    class Meta:
        model = StopLoss
        fields = ('symbol', 'market')


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet,
                   DelegatedAccountMixin):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]
    serializer_class = OrderSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = OrderFilter

    def get_queryset(self):
        account, variant = self.get_account_variant(self.request)

        filters = {}
        if variant:
            filters = {'wallet__variant': variant}
        elif self.request.get('agent') and self.request.get('strategy'):
            reserve_wallet = ReserveWallet.objects.filter(
                request_id=f'strategy:{self.request.get("strategy")}:{self.request.get("agent")}').first()
            if reserve_wallet:
                filters = {'wallet__variant': reserve_wallet.group_id}

        return Order.objects.filter(
            wallet__account=account,
            **filters
        ).select_related('symbol', 'wallet', 'stop_loss').order_by('-created')

    def get_serializer_context(self):
        account, variant = self.get_account_variant(self.request)
        return {
            **super(OrderViewSet, self).get_serializer_context(),
            'account': account,
            'trades': Trade.get_account_orders_filled_price(account),
            'variant': variant,
        }


class OpenOrderListAPIView(APIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    def get(self, request, *args, **kwargs):
        context = {
            'trades': Trade.get_account_orders_filled_price(self.request.user.account),
        }
        filters = {}
        symbol_filter = self.request.query_params.get('symbol')
        side_filter = self.request.query_params.get('side')
        bot_filter = self.request.query_params.get('bot')
        if symbol_filter:
            filters['symbol__name'] = symbol_filter.upper()
        if side_filter:
            filters['side'] = side_filter
        if bot_filter:
            filters['wallet__variant__isnull'] = not(str(bot_filter) == 'true')

        open_orders = Order.open_objects.filter(
            wallet__account=self.request.user.account, stop_loss__isnull=True, **filters
        ).select_related('symbol', 'wallet',)
        open_stop_losses = StopLoss.open_objects.filter(
            wallet__account=self.request.user.account, **filters
        ).select_related('symbol', 'wallet')
        serialized_orders = OrderStopLossSerializer(open_orders, many=True, context=context)
        serialized_stop_losses = OrderStopLossSerializer(open_stop_losses, many=True, context=context)
        DATE_PATTERN = '%Y-%m-%dT%H:%M:%S.%f%z'
        sorted_results = sorted(
            (serialized_orders.data + serialized_stop_losses.data),
            key=lambda obj: datetime.strptime(obj['created'], DATE_PATTERN), reverse=True
        )
        return Response(sorted_results)


class CancelOrderAPIView(CreateAPIView, DelegatedAccountMixin):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursAPIRateThrottle, SustainedAPIRateThrottle]

    serializer_class = CancelRequestSerializer
    queryset = CancelRequest.objects.all()

    def get_serializer_context(self):
        return {
            **super(CancelOrderAPIView, self).get_serializer_context(),
            'account': self.get_account_variant(self.request)[0],
            'allow_cancel_strategy_orders': user_has_delegate_permission(self.request.user)
        }


class StopLossViewSet(ModelViewSet, DelegatedAccountMixin):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    serializer_class = StopLossSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = StopLossFilter

    def get_queryset(self):
        return StopLoss.objects.filter(wallet__account=self.get_account_variant(self.request)[0]).order_by('-created')

    def get_serializer_context(self):
        account, variant = self.get_account_variant(self.request)
        return {
            **super(StopLossViewSet, self).get_serializer_context(),
            'account': account,
            'variant': variant,
        }
