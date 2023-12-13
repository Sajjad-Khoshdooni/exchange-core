import django_filters

from ledger.models import OTCTrade, OTCRequest
from market.serializers.trade_serializer import AccountTradeSerializer
from market.views import AccountTradeHistoryView
from rest_framework import serializers


class OTCFilter(django_filters.FilterSet):
    coin = django_filters.CharFilter(field_name='symbol__asset__symbol', lookup_expr='iexact')

    class Meta:
        model = OTCRequest
        fields = ('coin', 'side')


class OTCRequestSerializer(AccountTradeSerializer):
    from_asset = serializers.CharField(source='from_asset.symbol')
    to_asset = serializers.CharField(source='to_asset.symbol')

    class Meta(AccountTradeSerializer.Meta):
        model = OTCRequest
        fields = (*AccountTradeSerializer.Meta.fields, 'from_asset', 'to_asset')
        ref_name = 'OTCHistoryRequestSerializer'  # Unique name


class OTCHistoryView(AccountTradeHistoryView):
    filter_class = OTCFilter
    serializer_class = OTCRequestSerializer

    def get_queryset(self):

        if getattr(self, 'swagger_fake_view', False):
            return OTCRequest.objects.none()

        return OTCRequest.objects.filter(
            otctrade__status=OTCTrade.DONE,
            account=self.request.user.get_account(),
        ).select_related('symbol', 'symbol__asset', 'symbol__base_asset').order_by('-created')
