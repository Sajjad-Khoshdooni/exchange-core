import django_filters

from ledger.models import OTCTrade, OTCRequest
from market.views import AccountTradeHistoryView


class AccountTradeFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', lookup_expr='iexact')

    class Meta:
        model = OTCRequest
        fields = ('symbol', 'side')


class OTCHistoryView(AccountTradeHistoryView):
    filter_class = AccountTradeFilter

    def get_queryset(self):
        return OTCRequest.objects.filter(
            otctrade__status=OTCTrade.DONE,
            account=self.request.user.account,
        ).select_related('symbol', 'symbol__asset', 'symbol__base_asset').order_by('-created')
