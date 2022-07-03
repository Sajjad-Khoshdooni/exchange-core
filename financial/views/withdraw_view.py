import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from yekta_config.config import config

from accounts.models import VerificationCode
from accounts.permissions import IsBasicVerified
from accounts.verifiers.legal import is_48h_rule_passed
from financial.models import FiatWithdrawRequest
from financial.models.bank_card import BankAccount, BankAccountSerializer
from financial.utils.withdraw_limit import user_reached_fiat_withdraw_limit
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset
from ledger.utils.wallet_pipeline import WalletPipeline

logger = logging.getLogger(__name__)

MIN_WITHDRAW = 100_000


class WithdrawRequestSerializer(serializers.ModelSerializer):
    iban = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True)

    def create(self, validated_data):
        if config('WITHDRAW_ENABLE', '1') == '0':
            raise ValidationError('در حال حاضر امکان برداشت وجود ندارد.')

        user = self.context['request'].user

        if user.level < user.LEVEL2:
            raise ValidationError('برای برداشت ابتدا احراز هویت نمایید.')

        amount = validated_data['amount']
        iban = validated_data['iban']
        code = validated_data['code']

        bank_account = get_object_or_404(BankAccount, iban=iban, user=user)

        assert user.account.is_ordinary_user()

        if not is_48h_rule_passed(user):
            logger.info('FiatRequest rejected due to 48h rule. user=%s' % user.id)
            raise ValidationError('از اولین واریز ریالی حداقل باید دو روز کاری بگذرد.')

        if not bank_account.verified:
            logger.info('FiatRequest rejected due to unverified bank account. user=%s' % user.id)
            raise ValidationError({'iban': 'شماره حساب تایید نشده است.'})

        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_FIAT_WITHDRAW)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است'})

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
        withdraw_amount = amount - fee_amount

        try:
            with WalletPipeline() as pipeline:  # type: WalletPipeline
                withdraw_request = FiatWithdrawRequest.objects.create(
                    amount=withdraw_amount,
                    fee_amount=fee_amount,
                    bank_account=bank_account,
                    withdraw_channel=config('WITHDRAW_CHANNEL')
                )

                pipeline.new_lock(key=withdraw_request.group_id, wallet=wallet, amount=amount, reason=WalletPipeline.WITHDRAW)

        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست'})

        if otp_code:
            otp_code.set_code_used()

        from financial.tasks import process_withdraw

        if not settings.DEBUG_OR_TESTING:
            process_withdraw.s(withdraw_request.id).apply_async(countdown=FiatWithdrawRequest.FREEZE_TIME)

        return withdraw_request

    class Meta:
        model = FiatWithdrawRequest
        fields = ('iban', 'amount', 'code')


class WithdrawRequestView(ModelViewSet):
    permission_classes = (IsBasicVerified,)
    serializer_class = WithdrawRequestSerializer

    def get_queryset(self):
        return FiatWithdrawRequest.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if timezone.now() - timedelta(seconds=FiatWithdrawRequest.FREEZE_TIME) > instance.created:
            raise ValidationError('زمان مجاز برای لغو درخواست برداشت گذشته است.')

        if instance.status in (FiatWithdrawRequest.PENDING, FiatWithdrawRequest.DONE):
            raise ValidationError('امکان لغو درخواست برداشت وجود ندارد.')

        instance.change_status(FiatWithdrawRequest.CANCELED)

        return Response({'msg': 'FiatWithdrawRequest Deleted'}, status=status.HTTP_204_NO_CONTENT)


class WithdrawHistorySerializer(serializers.ModelSerializer):
    bank_account = BankAccountSerializer()
    rial_estimate_receive_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = FiatWithdrawRequest
        fields = ('id', 'created', 'status', 'fee_amount', 'amount', 'bank_account', 'ref_id',
                  'rial_estimate_receive_time',)

    def get_rial_estimate_receive_time(self, fiat_withdraw_request: FiatWithdrawRequest):
        return fiat_withdraw_request.withdraw_datetime and \
               fiat_withdraw_request.channel_handler.get_estimated_receive_time(fiat_withdraw_request.withdraw_datetime)

    def get_status(self, withdraw: FiatWithdrawRequest):
        if withdraw.status == FiatWithdrawRequest.PENDING:
            return FiatWithdrawRequest.DONE
        else:
            return withdraw.status


class WithdrawHistoryView(ListAPIView):
    serializer_class = WithdrawHistorySerializer
    pagination_class = LimitOffsetPagination

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status']

    def get_queryset(self):
        return FiatWithdrawRequest.objects.filter(bank_account__user=self.request.user).order_by('-created')
