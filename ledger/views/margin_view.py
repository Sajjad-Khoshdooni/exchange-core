from decimal import Decimal

from django.db.models import F, Sum
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.models import SystemConfig
from ledger.exceptions import InsufficientBalance
from ledger.margin.margin_info import MarginInfo
from ledger.models import MarginTransfer, Asset, Wallet, MarginPosition, MarginLeverage
from ledger.models.asset import CoinField, AssetSerializerMini
from ledger.models.margin import SymbolField
from ledger.models.position import MarginHistoryModel
from ledger.utils.fields import get_serializer_amount_field
from ledger.utils.margin import check_margin_view_permission
from ledger.utils.precision import floor_precision, get_presentation_amount, get_margin_coin_presentation_balance
from ledger.utils.price import get_last_price, get_last_prices, get_coins_symbols


class MarginInfoView(APIView):

    @staticmethod
    def aggregate_wallets_values(wallets, prices):
        total_irt_value = total_usdt_value = Decimal(0)
        for wallet in wallets:
            coin = wallet.asset.symbol
            price_usdt = prices.get(coin + Asset.USDT, 0)
            price_irt = prices.get(coin + Asset.IRT, 0)

            total_usdt_value += wallet.balance * price_usdt
            total_irt_value += wallet.balance * price_irt
        return {
            'IRT': get_presentation_amount(floor_precision(total_irt_value)),
            'USDT': get_presentation_amount(floor_precision(total_usdt_value, 2))
        }

    def get(self, request: Request):
        account = request.user.get_account()

        user_margin_wallets = Wallet.objects.filter(market=Wallet.MARGIN, account=account)

        coins = list(user_margin_wallets.values_list('asset__symbol', flat=True))
        prices = get_last_prices(get_coins_symbols(coins))

        total_asset = self.aggregate_wallets_values(user_margin_wallets.filter(balance__gt=Decimal('0')), prices)
        total_debt = self.aggregate_wallets_values(user_margin_wallets.filter(balance__lt=Decimal('0')), prices)

        return Response({
            'total_assets': total_asset,
            'total_equity': {
                'IRT': get_presentation_amount(Decimal(total_asset['IRT']) + Decimal(total_debt['IRT'])),
                'USDT': get_presentation_amount(Decimal(total_asset['USDT']) + Decimal(total_debt['USDT'])),
            }
        })


class AssetMarginInfoView(APIView):
    def get(self, request: Request, symbol):
        account = request.user.get_account()
        asset = get_object_or_404(Asset, symbol=symbol.upper())

        margin_info = MarginInfo.get(account)

        margin_wallet = asset.get_wallet(account, Wallet.MARGIN)
        loan_wallet = asset.get_wallet(account, Wallet.LOAN)

        price = get_last_price(asset.symbol + Asset.USDT)

        if asset.symbol != Asset.USDT:
            price = price * Decimal('1.002')

        max_borrow = max(margin_info.get_max_borrowable() / price, Decimal(0))
        max_transfer = min(margin_wallet.get_free(), max(margin_info.get_max_transferable() / price, Decimal(0)))

        return Response({
            'balance': margin_wallet.get_free(),
            'debt': -loan_wallet.get_free(),
            'max_borrow': max_borrow,
            'max_transfer': max_transfer,
        })


class MarginTransferSerializer(serializers.ModelSerializer):
    amount = get_serializer_amount_field()
    coin = CoinField(source='asset')
    symbol = SymbolField(source='position_symbol', required=False)
    asset = AssetSerializerMini(read_only=True)

    def create(self, validated_data):
        user = self.context['request'].user

        symbol = validated_data.get('position_symbol')
        check_margin_view_permission(user.get_account(), symbol)

        return super(MarginTransferSerializer, self).create(validated_data)

    def validate(self, attrs):
        if attrs['asset'] not in Asset.objects.filter(symbol__in=[Asset.IRT, Asset.USDT]):
            raise ValidationError({'asset': 'فقط میتوانید ریال و تتر انتقال دهید.'})

        if attrs['type'] not in [MarginTransfer.SPOT_TO_MARGIN, MarginTransfer.MARGIN_TO_SPOT] and not attrs.get('position_symbol'):
            raise ValidationError({'position_symbol': 'بازار را وارد کنید'})

        if attrs['type'] == MarginTransfer.SPOT_TO_MARGIN:
            if not self.context['request'].user.show_margin:
                raise ValidationError('Dont Have allow to Transfer Margin')

            user_total_equity = MarginPosition.objects.filter(
                account=self.context['request'].user.get_account(),
                status__in=[MarginPosition.TERMINATING, MarginPosition.OPEN],
                symbol__base_asset=attrs.get('asset')
            ).annotate(base_asset_value=F('asset_wallet__balance') * F('symbol__last_trade_price')).\
                aggregate(total_equity=Sum('base_asset_value') + Sum('base_wallet__balance'))['total_equity'] or 0

            base = attrs.get('asset').symbol
            sys_config = SystemConfig.get_system_config()

            if (base == Asset.USDT and user_total_equity >= sys_config.total_user_margin_usdt_base) or \
                    (base == Asset.IRT and user_total_equity >= sys_config.total_user_margin_irt_base):
                raise ValidationError('Cant place margin order Due to reach total Equity limit')

        if attrs['type'] in [MarginTransfer.POSITION_TO_MARGIN, MarginTransfer.MARGIN_TO_POSITION]:
            if attrs['position_symbol'].base_asset != attrs['asset']:
                asset = attrs['position_symbol'].base_asset.name_fa
                raise ValidationError({'asset': f'فقط میتوانید {asset} انتقال دهید.'})

            position = MarginPosition.objects.filter(
                account=self.context['request'].user.get_account(),
                symbol=attrs['position_symbol'],
                status__in=[MarginPosition.OPEN],
            ).first()

            if not position:
                raise ValidationError('There is no valid position to transfer margin')

            if attrs['type'] == MarginTransfer.POSITION_TO_MARGIN and position.withdrawable_base_asset < Decimal(attrs['amount']):
                raise ValidationError(f'You can only transfer: {position.withdrawable_base_asset}')
        return attrs

    class Meta:
        model = MarginTransfer
        fields = ('created', 'amount', 'type', 'coin', 'asset', 'symbol')
        read_only_fields = ('created', )


class MarginTransferViewSet(ModelViewSet):
    serializer_class = MarginTransferSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

    def perform_create(self, serializer):
        try:
            serializer.save(account=self.request.user.get_account())
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')

    def get_queryset(self):
        return MarginTransfer.objects.filter(
            account=self.request.user.get_account()
        ).order_by('-created')


class MarginPositionInfoView(APIView):
    def get(self, request: Request):
        account = request.user.get_account()
        symbol = request.GET.get('symbol')
        side = request.GET.get('side')

        if not symbol:
            return Response({'Error': 'need symbol'}, 400)
        if not side:
            return Response({'Error': 'need position side'}, 400)

        from market.models import PairSymbol
        symbol_model = get_object_or_404(PairSymbol, name=symbol)

        free = symbol_model.base_asset.get_wallet(
            account, Wallet.MARGIN, None
        ).get_free()
        margin_leverage, _ = MarginLeverage.objects.get_or_create(account=account)

        data = {
            'max_buy_volume': free * margin_leverage.leverage,
            'max_sell_volume': free * margin_leverage.leverage / symbol_model.last_trade_price
        }

        data["max_buy_volume"] = get_margin_coin_presentation_balance(symbol_model.base_asset.symbol,
                                                               max(Decimal('0'), data['max_buy_volume']) * Decimal('0.99'))
        data["max_sell_volume"] = get_margin_coin_presentation_balance(symbol_model.asset.symbol,
                                                                max(Decimal('0'), data['max_sell_volume']) * Decimal('0.99'))
        return Response(data)


class MarginHistorySerializer(serializers.ModelSerializer):
    symbol = serializers.SerializerMethodField()

    def get_symbol(self, instance):
        return instance.asset.symbol

    class Meta:
        model = MarginHistoryModel
        fields = ('created', 'amount', 'symbol', 'type', 'position')


class MarginPositionInterestHistoryView(ListAPIView):
    serializer_class = MarginHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

    def get_queryset(self):
        account = self.request.user.get_account()
        queryset = MarginHistoryModel.objects.filter(position__account=account)

        id = self.request.query_params.get('id')
        if id:
            queryset = queryset.filter(position__id=id)

        return queryset.order_by('-created')


class LeverageViewSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        if not 1 <= Decimal(attrs.get('leverage')) <= 5 or Decimal(attrs.get('leverage')) - int(attrs.get('leverage')) != Decimal('0'):
            raise ValidationError('ضریب باید عددی صحیحی بین ۱ و ۵ باشد.')

        return attrs

    class Meta:
        model = MarginLeverage
        fields = ('leverage',)


class MarginLeverageView(APIView):
    def post(self, request):
        serializer = LeverageViewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        MarginLeverage.objects.update_or_create(
            account=request.user.account,
            defaults={
                'leverage': data['leverage']
            }
        )

        return Response(200)

    def get(self, request):
        margin_leverage, _ = MarginLeverage.objects.get_or_create(account=request.user.account)
        sys_config = SystemConfig.get_system_config()

        return Response({
            "leverage": margin_leverage.leverage,
            "max_leverage": sys_config.max_margin_leverage
        }, 200)

