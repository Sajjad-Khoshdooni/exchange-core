import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from market.models import PairSymbol
from market.serializers.symbol_serializer import SymbolSerializer, SymbolBreifStatsSerializer, SymbolStatsSerializer


class SymbolFilter(django_filters.FilterSet):
    asset = django_filters.CharFilter(field_name='asset__symbol')
    base_asset = django_filters.CharFilter(field_name='base_asset__symbol')

    class Meta:
        model = PairSymbol
        fields = ('name', 'asset', 'base_asset', 'enable')


class SymbolListAPIView(ListAPIView):
    filter_backends = [DjangoFilterBackend]
    filter_class = SymbolFilter
    queryset = PairSymbol.objects.all()

    def get_serializer_class(self):
        if self.request.query_params.get('stats') == '1':
            return SymbolBreifStatsSerializer
        else:
            return SymbolSerializer


class SymbolDetailedStatsAPIView(RetrieveAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    serializer_class = SymbolStatsSerializer
    queryset = PairSymbol.objects.all()
    lookup_field = 'name'
