import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from market.models import StopLoss
from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from accounts.views.authentication import CustomTokenAuthentication
from market.models import Order, CancelRequest
from market.serializers.cancel_request_serializer import CancelRequestSerializer
from market.serializers.order_serializer import OrderSerializer
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
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication)
    pagination_class = LimitOffsetPagination
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]
    serializer_class = OrderSerializer

    filter_backends = [DjangoFilterBackend]
    filter_class = OrderFilter

    def get_queryset(self):
        return Order.objects.filter(wallet__account=self.request.user.account).order_by('-created')

    def get_serializer_context(self):
        return {
            **super(OrderViewSet, self).get_serializer_context(),
            'account': self.request.user.account
        }


class CancelOrderAPIView(CreateAPIView):
    authentication_classes = (SessionAuthentication, CustomTokenAuthentication)
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = CancelRequestSerializer
    queryset = CancelRequest.objects.all()

    def get_serializer_context(self):
        return {
            **super(CancelOrderAPIView, self).get_serializer_context(),
            'account': self.request.user.account
        }


class StopLossViewSet(ModelViewSet):
    authentication_classes = (SessionAuthentication,)
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
