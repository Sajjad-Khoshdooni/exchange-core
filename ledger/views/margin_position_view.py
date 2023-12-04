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
    balance = serializers.SerializerMethodField()
    base_debt = serializers.SerializerMethodField()
    asset_debt = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    coin_amount = serializers.SerializerMethodField()
    liquidation_price = serializers.SerializerMethodField()
    pnl = serializers.SerializerMethodField()

    def get_margin_ratio(self, instance: MarginPosition):
        if instance.base_debt_amount:
            ratio = instance.base_total_balance / instance.base_debt_amount
            return floor_precision(abs(ratio), 2)
        return None

    def get_balance(self, instance):
        return instance.equity

    def get_base_debt(self, instance):
        return instance.base_debt_amount

    def get_asset_debt(self, instance):
        return instance.loan_wallet.balance

    def get_amount(self, instance):
        return abs(floor_precision(instance.base_debt_amount / instance.symbol.last_trade_price, instance.symbol.tick_size))

    def get_liquidation_price(self, instance):
        return floor_precision(instance.liquidation_price, instance.symbol.step_size)

    def get_coin_amount(self, instance):
        return floor_precision(abs(instance.asset_wallet.balance), instance.symbol.tick_size)

    def get_pnl(self, instance):
        return instance.base_total_balance + instance.base_debt_amount - instance.net_amount

    class Meta:
        model = MarginPosition
        fields = ('created', 'account', 'asset_wallet', 'base_wallet', 'symbol', 'amount', 'average_price',
                  'liquidation_price', 'side', 'status', 'id', 'margin_ratio', 'balance', 'base_debt', 'asset_debt',
                  'leverage', 'coin_amount', 'pnl')


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
        return MarginPosition.objects.filter(account=self.request.user.get_account(),
                                             liquidation_price__isnull=False, status=MarginPosition.OPEN)


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

        return attrs


class MarginClosePositionView(APIView):
    def post(self, request):
        serializer = MarginClosePositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with WalletPipeline() as pipeline:
            serializer.position.liquidate(pipeline=pipeline, charge_insurance=False)

        return Response(200)
