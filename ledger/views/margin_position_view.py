import django_filters

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet

from ledger.models import MarginPosition
from ledger.models.asset import AssetSerializerMini


class MarginPositionSerializer(AssetSerializerMini):
    class Meta:
        model = MarginPosition
        fields = ('created', 'account', 'wallet', 'symbol', 'amount', 'average_price', 'liquidation_price', 'side',
                  'status')


class MarginPositionFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', lookup_expr='iexact')
    created_after = django_filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    created = django_filters.IsoDateTimeFromToRangeFilter()

    class Meta:
        model = MarginPosition
        fields = ('symbol', 'status', 'side', 'created_after')


class MarginPositionViewSet(ModelViewSet):
    serializer_class = MarginPositionSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = MarginPositionFilter

    def get_queryset(self):
        return MarginPosition.objects.filter(account=self.request.user.get_account())
