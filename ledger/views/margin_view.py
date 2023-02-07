from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from ledger.exceptions import InsufficientBalance, InsufficientDebt, MaxBorrowableExceeds, HedgeError
from ledger.margin.margin_info import MarginInfo
from ledger.models import MarginTransfer, Asset, MarginLoan, Wallet, CloseRequest
from ledger.models.asset import CoinField, AssetSerializerMini
from ledger.utils.external_price import get_external_price, SELL
from ledger.utils.fields import get_serializer_amount_field
from ledger.utils.margin import check_margin_view_permission


class MarginInfoView(APIView):
    def get(self, request: Request):
        account = request.user.account
        margin_info = MarginInfo.get(account)

        margin_level = min(margin_info.get_margin_level(), Decimal(999))

        if margin_level > 10:
            margin_level_precision = 0
        elif margin_level > 2:
            margin_level_precision = 1
        else:
            margin_level_precision = 3

        return Response({
            'total_assets': round(Decimal(margin_info.total_assets), 2),
            'total_debt': round(Decimal(margin_info.total_debt), 2),
            'margin_level': round(margin_level, margin_level_precision),
            'total_equity': round(Decimal(margin_info.get_total_equity()), 2),
            'has_position': Wallet.objects.filter(account=account, market=Wallet.LOAN, balance__lt=0).exists()
        })


class AssetMarginInfoView(APIView):
    def get(self, request: Request, symbol):
        account = request.user.account
        asset = get_object_or_404(Asset, symbol=symbol.upper(), margin_enable=True)

        margin_info = MarginInfo.get(account)

        margin_wallet = asset.get_wallet(account, Wallet.MARGIN)
        loan_wallet = asset.get_wallet(account, Wallet.LOAN)

        price = get_external_price(asset.symbol, base_coin=Asset.USDT, side=SELL)

        if asset.symbol != Asset.USDT:
            price = price * Decimal('1.002')

        max_borrow = max(margin_info.get_max_borrowable() / price, Decimal(0))
        max_transfer = min(margin_wallet.get_free(), max(margin_info.get_max_transferable() / price, Decimal(0)))

        return Response({
            'balance': asset.get_presentation_amount(margin_wallet.get_free()),
            'debt': asset.get_presentation_amount(-loan_wallet.get_free()),
            'max_borrow': asset.get_presentation_amount(max_borrow),
            'max_transfer': asset.get_presentation_amount(max_transfer),
        })


class MarginTransferSerializer(serializers.ModelSerializer):
    amount = get_serializer_amount_field()
    coin = CoinField(source='asset')
    asset = AssetSerializerMini(read_only=True)

    def create(self, validated_data):
        user = self.context['request'].user

        asset = validated_data['asset']

        check_margin_view_permission(user.account, asset)

        return super(MarginTransferSerializer, self).create(validated_data)

    class Meta:
        model = MarginTransfer
        fields = ('created', 'amount', 'type', 'coin', 'asset')
        read_only_fields = ('created', )


class MarginTransferViewSet(ModelViewSet):
    serializer_class = MarginTransferSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type']

    def perform_create(self, serializer):
        try:
            serializer.save(account=self.request.user.account)
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')

    def get_queryset(self):
        return MarginTransfer.objects.filter(
            account=self.request.user.account
        ).order_by('-created')


class MarginLoanSerializer(serializers.ModelSerializer):
    coin = CoinField(source='asset')
    amount = get_serializer_amount_field()
    asset = AssetSerializerMini(read_only=True)

    def create(self, validated_data):
        user = self.context['request'].user
        asset = validated_data['asset']

        check_margin_view_permission(user.account, asset)

        validated_data['loan_type'] = validated_data.pop('type')

        if validated_data['amount'] <= 0:
            raise ValidationError('مقداری بزرگتر از صفر انتخاب کنید.')

        try:
            return MarginLoan.new_loan(
                **validated_data
            )
        except InsufficientDebt:
            raise ValidationError('میزان بدهی کمتر از مقدار بازپرداخت است.')
        except MaxBorrowableExceeds:
            raise ValidationError('میزان بدهی بیشتر از حد مجاز است.')
        except HedgeError:
            raise ValidationError('مشکلی در پردازش اطلاعات به وجود آمد.')

    class Meta:
        fields = ('created', 'amount', 'type', 'coin', 'asset', 'status')
        read_only_fields = ('created', 'status')
        model = MarginLoan


class MarginLoanViewSet(ModelViewSet):
    serializer_class = MarginLoanSerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'type']

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account)

    def get_queryset(self):
        return MarginLoan.objects.filter(
            account=self.request.user.account
        ).order_by('-created')


class MarginClosePositionView(APIView):
    def post(self, request: Request):
        account = request.user.account

        CloseRequest.close_margin(account, reason=CloseRequest.USER)

        return Response('ok', status=201)
