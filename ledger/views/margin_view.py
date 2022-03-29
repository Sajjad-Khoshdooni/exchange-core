from decimal import Decimal

from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from ledger.exceptions import InsufficientBalance, InsufficientDebt, MaxBorrowableExceeds
from ledger.models import MarginTransfer, Asset, MarginLoan, Wallet
from ledger.utils.margin import MarginInfo
from ledger.utils.price import get_trading_price_usdt, BUY


class MarginInfoView(APIView):
    def get(self, request: Request):
        account = request.user.account
        margin_info = MarginInfo.get(account)

        return Response({
            'total_assets': round(margin_info.total_assets, 2),
            'total_debt': round(margin_info.total_debt, 2),
            'margin_level': round(margin_info.get_margin_level(), 2),
            'total_equity': round(margin_info.get_total_equity(), 2),
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

    class Meta:
        fields = ('amount', 'type')
        model = MarginTransfer


class MarginTransferView(CreateAPIView):
    serializer_class = MarginTransferSerializer

    def perform_create(self, serializer):
        try:
            serializer.save(account=self.request.user.account)
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')


class MarginLoanSerializer(serializers.ModelSerializer):
    coin = serializers.CharField(write_only=True)

    def validate(self, attrs):
        coin = attrs.pop('coin')
        asset = get_object_or_404(Asset, symbol=coin)

        return {
            **attrs,
            'asset': asset
        }

    def create(self, validated_data):
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
        fields = ('amount', 'type', 'coin')
        model = MarginLoan


class MarginLoanView(CreateAPIView):
    serializer_class = MarginLoanSerializer

    def perform_create(self, serializer):
        serializer.save(account=self.request.user.account)
