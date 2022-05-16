import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView, RetrieveAPIView

from accounts.throttle import BursApiRateThrottle, SustaineApiRatethrottle
from market.models import PairSymbol
from market.serializers.symbol_serializer import SymbolSerializer, SymbolBreifStatsSerializer, SymbolStatsSerializer


class SymbolFilter(django_filters.FilterSet):
    asset = django_filters.CharFilter(field_name='asset__symbol')
    base_asset = django_filters.CharFilter(field_name='base_asset__symbol')

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'enable')


class SymbolListAPIView(ListAPIView):
    authentication_classes = ()
    permission_classes = ()
    filter_backends = [DjangoFilterBackend]
    filter_class = SymbolFilter
    queryset = PairSymbol.objects.all().order_by('-asset__trend', 'asset__order', 'base_asset__trend', '-base_asset__order')

    def get_serializer_class(self):
        if self.request.query_params.get('stats') == '1':
            return SymbolBreifStatsSerializer
        else:
            return SymbolSerializer


class SymbolDetailedStatsAPIView(RetrieveAPIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = [BursApiRateThrottle, SustaineApiRatethrottle]

    serializer_class = SymbolStatsSerializer
    queryset = PairSymbol.objects.all()
    lookup_field = 'name'
