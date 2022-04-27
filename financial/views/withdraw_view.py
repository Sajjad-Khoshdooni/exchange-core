from datetime import timedelta

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404, ListAPIView, DestroyAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsBasicVerified
from accounts.utils.admin import url_to_edit_object
from accounts.utils.telegram import send_support_message
from accounts.verifiers.legal import is_48h_rule_passed
from financial.models import FiatWithdrawRequest
from financial.models.bank_card import BankAccount, BankAccountSerializer
from financial.utils.withdraw_limit import user_reached_fiat_withdraw_limit, get_fiat_estimate_receive_time
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset
from ledger.utils.precision import humanize_number

import logging

logger = logging.getLogger(__name__)


MIN_WITHDRAW = 100_000


class WithdrawRequestSerializer(serializers.ModelSerializer):
    iban = serializers.CharField(write_only=True)

    def create(self, validated_data):
        amount = validated_data['amount']
        iban = validated_data['iban']

        user = self.context['request'].user
        bank_account = get_object_or_404(BankAccount, iban=iban, user=user)

        assert user.account.is_ordinary_user()

        if not is_48h_rule_passed(user):
            logger.info('FiatRequest rejected due to 48h rule. user=%s' % user.id)
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

        if not bank_account.verified:
            logger.info('FiatRequest rejected due to unverified bank account. user=%s' % user.id)
            raise ValidationError({'iban': 'شماره حساب تایید نشده است.'})

        if amount < MIN_WITHDRAW:
            logger.info('FiatRequest rejected due to small amount. user=%s' % user.id)
            raise ValidationError({'iban': 'مقدار وارد شده کمتر از حد مجاز است.'})

        if user_reached_fiat_withdraw_limit(user, amount):
            logger.info('FiatRequest rejected due to max withdraw limit reached. user=%s' % user.id)
            raise ValidationError({'amount': 'شما به سقف برداشت ریالی خورده اید.'})

        asset = Asset.get(Asset.IRT)
        wallet = asset.get_wallet(user.account)

        # fee_amount = min(4000, int(amount * 0.01))
        fee_amount = 5000

        try:
            lock = wallet.lock_balance(amount)
        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست'})

        withdraw_amount = amount - fee_amount

        withdraw_request = FiatWithdrawRequest.objects.create(
            amount=withdraw_amount,
            fee_amount=fee_amount,
            lock=lock,
            bank_account=bank_account
        )

        link = url_to_edit_object(withdraw_request)
        send_support_message(
            message='درخواست برداشت ریالی به ارزش %s تومان ایجاد شد.' % humanize_number(withdraw_amount),
            link=link
        )

        return withdraw_request

    class Meta:
        model = FiatWithdrawRequest
        fields = ('iban', 'amount')


class WithdrawRequestView(ModelViewSet):
    permission_classes = (IsBasicVerified, )
    serializer_class = WithdrawRequestSerializer

    def get_queryset(self):
        return FiatWithdrawRequest.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if timezone.now() - timedelta(minutes=3) > instance.created:
            raise ValidationError('زمان مجاز برای حذف درخواست برداشت گذشته است.')

        instance.deleted = True
        instance.save()

        return Response({'msg': 'FiatWithdrawRequest Deleted'}, status=status.HTTP_204_NO_CONTENT)


class WithdrawHistorySerializer(serializers.ModelSerializer):
    bank_account = BankAccountSerializer()
    rial_estimate_receive_time = serializers.SerializerMethodField()

    class Meta:
        model = FiatWithdrawRequest
        fields = ('id', 'created', 'status', 'fee_amount', 'amount', 'bank_account', 'ref_id', 'rial_estimate_receive_time', )

    def get_rial_estimate_receive_time(self, fiat_withdraw_request: FiatWithdrawRequest):
        return get_fiat_estimate_receive_time(fiat_withdraw_request.created)


class WithdrawHistoryView(ListAPIView):
    serializer_class = WithdrawHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        return FiatWithdrawRequest.objects.filter(bank_account__user=self.request.user).order_by('-created')
