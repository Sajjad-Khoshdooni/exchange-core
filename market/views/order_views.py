from datetime import datetime

import django_filters
from django.db.models import F, Sum
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

from market.models import StopLoss, Trade
from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from market.models import Order, CancelRequest
from market.serializers.cancel_request_serializer import CancelRequestSerializer
from market.serializers.order_serializer import OrderSerializer
from market.serializers.order_stoploss_serializer import OrderStopLossSerializer
from market.serializers.stop_loss_serializer import StopLossSerializer


class OrderFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name')
    market = django_filters.CharFilter(field_name='wallet__market')

    class Meta:
        model = Order
        fields = ('symbol', 'status', 'market')


class StopLossFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name')
    market = django_filters.CharFilter(field_name='wallet__market')

    class Meta:
        model = StopLoss
        fields = ('symbol', 'market')


class OrderViewSet(mixins.CreateModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.ListModelMixin,
                   GenericViewSet):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]
    serializer_class = OrderSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = OrderFilter

    def get_queryset(self):
        return Order.objects.filter(
            wallet__account=self.request.user.account
        ).select_related('symbol', 'wallet').order_by('-created')

    def get_serializer_context(self):
        trades = {
            trade['order_id']: (trade['sum_amount'], trade['sum_value']) for trade in
            Trade.objects.filter(account=self.request.user.account).annotate(
                value=F('amount') * F('price')
            ).values('order').annotate(sum_amount=Sum('amount'), sum_value=Sum('value')).values(
                'order_id', 'sum_amount', 'sum_value'
            )
        }
        return {
            **super(OrderViewSet, self).get_serializer_context(),
            'account': self.request.user.account,
            'trades': Trade.get_account_orders_filled_price(self.request.user.account),
        }


class OpenOrderListAPIView(APIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication)
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    def get(self, request, *args, **kwargs):
        context = {
            'trades': Trade.get_account_orders_filled_price(self.request.user.account),
        }
        open_orders = Order.open_objects.filter(wallet__account=self.request.user.account)
        open_stop_losses = StopLoss.open_objects.filter(wallet__account=self.request.user.account)
        serialized_orders = OrderStopLossSerializer(open_orders, many=True, context=context)
        serialized_stop_losses = OrderStopLossSerializer(open_stop_losses, many=True, context=context)
        DATE_PATTERN = '%Y-%m-%dT%H:%M:%S.%f%z'
        sorted_results = sorted(
            (serialized_orders.data + serialized_stop_losses.data),
            key=lambda obj: datetime.strptime(obj['created'], DATE_PATTERN), reverse=True
        )
        return Response(sorted_results)


class CancelOrderAPIView(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication, JWTAuthentication)
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = CancelRequestSerializer
    queryset = CancelRequest.objects.all()

    def get_serializer_context(self):
        return {
            **super(CancelOrderAPIView, self).get_serializer_context(),
            'account': self.request.user.account
        }


class StopLossViewSet(ModelViewSet):
    authentication_classes = (SessionAuthentication, JWTAuthentication)
    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    serializer_class = StopLossSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = StopLossFilter

    def get_queryset(self):
        return StopLoss.objects.filter(wallet__account=self.request.user.account).order_by('-created')

    def get_serializer_context(self):
        return {
            **super(StopLossViewSet, self).get_serializer_context(),
            'account': self.request.user.account
        }
