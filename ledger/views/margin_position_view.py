import django_filters
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.models import MarginPosition
from ledger.models.asset import AssetSerializerMini
from ledger.utils.precision import floor_precision
from ledger.utils.wallet_pipeline import WalletPipeline
from market.serializers.symbol_serializer import SymbolSerializer


class MarginPositionSerializer(AssetSerializerMini):
    symbol = SymbolSerializer()
    margin_ratio = serializers.SerializerMethodField()
    equity = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    debt = serializers.SerializerMethodField()

    def get_margin_ratio(self, instance):
        return floor_precision(instance.get_margin_ratio() or 0, 2)
    
    def get_equity(self, instance):
        return instance.equity

    def get_balance(self, instance):
        return instance.total_balance

    def get_debt(self, instance):
        return instance.debt_amount

    class Meta:
        model = MarginPosition
        fields = ('created', 'account', 'asset_wallet', 'base_wallet', 'symbol', 'amount', 'average_price',
                  'liquidation_price', 'side', 'status', 'id', 'margin_ratio', 'equity', 'balance', 'debt')


class MarginPositionFilter(django_filters.FilterSet):
    symbol = django_filters.CharFilter(field_name='symbol__name', lookup_expr='iexact')
    created_after = django_filters.DateTimeFilter(field_name='created', lookup_expr='gte')
    created = django_filters.IsoDateTimeFromToRangeFilter()

    class Meta:
        model = MarginPosition
        fields = ('symbol', 'status', 'created_after')


class MarginPositionViewSet(ModelViewSet):
    serializer_class = MarginPositionSerializer
    filter_backends = [DjangoFilterBackend]
    filter_class = MarginPositionFilter

    def get_queryset(self):
        return MarginPosition.objects.filter(account=self.request.user.get_account())


class MarginClosePositionSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    def __init__(self, *args, **kwargs):
        super(MarginClosePositionSerializer, self).__init__(*args, **kwargs)

        self.position = MarginPosition.objects.filter(id=kwargs.get('data', {})['id'], status=MarginPosition.OPEN).first()

    def validate(self, attrs):
        if not self.position:
            raise ValidationError(
                {'id': _('there is no open position with this Id.')}
            )


class MarginClosePositionView(APIView):
    def post(self, request):
        serializer = MarginClosePositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with WalletPipeline() as pipeline:
            serializer.position.liquidate(pipeline=pipeline, charge_insurance=False)

        return Response(200)
