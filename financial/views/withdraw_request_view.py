from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from accounts.permissions import IsBasicVerified
from financial.models import BankCard, PaymentRequest, Payment, FiatWithdrawRequest
from financial.models.bank_card import BankCardSerializer, BankAccount
from financial.models.gateway import GatewayFailed
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset

MIN_WITHDRAW = 15000


class WithdrawRequestSerializer(serializers.ModelSerializer):
    iban = serializers.CharField(write_only=True)

    def create(self, validated_data):
        amount = validated_data['amount']
        iban = validated_data['iban']

        user = self.context['request'].user
        bank_account = get_object_or_404(BankAccount, iban=iban, user=user)

        if not bank_account.verified:
            raise ValidationError({'iban': 'شماره حساب تایید نشده است.'})

        if amount < 15000:
            raise ValidationError({'iban': 'مقدار وارد شده کمتر از حد مجاز است.'})

        asset = Asset.get(Asset.IRT)
        wallet = asset.get_wallet(user.account)

        fee_amount = min(4000, int(amount * 0.01))

        try:
            lock = wallet.lock_balance(amount)
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست'})

        return FiatWithdrawRequest.objects.create(
            amount=amount - fee_amount,
            fee_amount=fee_amount,
            lock=lock,
            bank_account=bank_account
        )

    class Meta:
        model = FiatWithdrawRequest
        fields = ('iban', 'amount')


class WithdrawRequestView(CreateAPIView):
    permission_classes = (IsBasicVerified, )
    serializer_class = WithdrawRequestSerializer
