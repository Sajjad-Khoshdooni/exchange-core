from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet

from ledger.exceptions import InsufficientBalance, InsufficientDebt, MaxBorrowableExceeds
from ledger.models import MarginTransfer, Asset, MarginLoan, Wallet
from ledger.models.asset import CoinField
from ledger.utils.fields import SerializerDecimalField, get_serializer_amount_field
from ledger.utils.margin import MarginInfo
from ledger.utils.price import get_trading_price_usdt, BUY


class MarginInfoView(APIView):
    def get(self, request: Request):
        account = request.user.account
        margin_info = MarginInfo.get(account)

        return Response({
            'total_assets': round(margin_info.total_assets, 8),
            'total_debt': round(margin_info.total_debt, 8),
            'margin_level': round(margin_info.get_margin_level(), 2),
            'total_equity': round(margin_info.get_total_equity(), 8),
        })


class AssetMarginInfoView(APIView):
    def get(self, request: Request, symbol):
        account = request.user.account
        asset = get_object_or_404(Asset, symbol=symbol.upper())

        margin_info = MarginInfo.get(account)

        margin_wallet = asset.get_wallet(account, Wallet.MARGIN)
        loan_wallet = asset.get_wallet(account, Wallet.LOAN)

        price = get_trading_price_usdt(asset.symbol, BUY)
        max_borrow = max(margin_info.get_max_borrowable() / price, Decimal(0))
        max_transfer = max(margin_info.get_max_transferable() / price, Decimal(0))

        return Response({
            'balance': asset.get_presentation_amount(margin_wallet.get_free()),
            'debt': asset.get_presentation_amount(-loan_wallet.get_free()),
            'max_borrow': asset.get_presentation_amount(max_borrow),
            'max_transfer': asset.get_presentation_amount(max_transfer),
        })


class MarginTransferSerializer(serializers.ModelSerializer):
    amount = get_serializer_amount_field()

    class Meta:
        model = MarginTransfer
        fields = ('created', 'amount', 'type')
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

    def create(self, validated_data):
        user = self.context['request'].user

        if not user.margin_quiz_pass_date:
            raise ValidationError('شما باید ابتدا به سوالات این بخش پاسخ دهید.')

        validated_data['loan_type'] = validated_data.pop('type')

        try:
            return MarginLoan.new_loan(
                **validated_data
            )
        except InsufficientDebt:
            raise ValidationError('میزان بدهی کمتر از مقدار بازپرداخت است.')
        except MaxBorrowableExceeds:
            raise ValidationError('میزان بدهی بیشتر از حد مجاز است.')

    class Meta:
        fields = ('created', 'amount', 'type', 'coin', 'status')
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
