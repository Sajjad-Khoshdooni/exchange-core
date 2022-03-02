from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination

from accounts.permissions import IsBasicVerified
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from financial.models import FiatWithdrawRequest
from financial.models.bank_card import BankAccount, BankAccountSerializer
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset
from ledger.utils.precision import humanize_number

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

        if amount < MIN_WITHDRAW:
            raise ValidationError({'iban': 'مقدار وارد شده کمتر از حد مجاز است.'})

        asset = Asset.get(Asset.IRT)
        wallet = asset.get_wallet(user.account)

        # fee_amount = min(4000, int(amount * 0.01))
        fee_amount = 5000

        try:
            lock = wallet.lock_balance(amount)
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست'})

        withdraw_request = FiatWithdrawRequest.objects.create(
            amount=amount - fee_amount,
            fee_amount=fee_amount,
            lock=lock,
            bank_account=bank_account
        )

        link = url_to_edit_object(withdraw_request)
        send_support_message(
            message='درخواست برداشت ریالی به ارزش %s تومان ایجاد شد.' % humanize_number(amount),
            link=link
        )

        return withdraw_request

    class Meta:
        model = FiatWithdrawRequest
        fields = ('iban', 'amount')


class WithdrawRequestView(CreateAPIView):
    permission_classes = (IsBasicVerified, )
    serializer_class = WithdrawRequestSerializer


class WithdrawHistorySerializer(serializers.ModelSerializer):
    bank_account = BankAccountSerializer()

    class Meta:
        model = FiatWithdrawRequest
        fields = ('created', 'status', 'fee_amount', 'amount', 'bank_account', 'ref_id')


class WithdrawHistoryView(ListAPIView):
    serializer_class = WithdrawHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        return FiatWithdrawRequest.objects.filter(bank_account__user=self.request.user).order_by('-created')
