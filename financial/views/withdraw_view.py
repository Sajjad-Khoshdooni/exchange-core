import logging
from datetime import timedelta

from decouple import config
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from accounts.models import VerificationCode
from accounts.permissions import IsBasicVerified
from accounts.utils.auth2fa import is_2fa_active_for_user, code_2fa_verifier
from accounts.verifiers.legal import is_48h_rule_passed
from financial.models import FiatWithdrawRequest
from financial.models.bank_card import BankAccount, BankAccountSerializer
from financial.utils.withdraw_limit import user_reached_fiat_withdraw_limit
from financial.utils.withdraw_verify import auto_verify_fiat_withdraw
from ledger.exceptions import InsufficientBalance
from ledger.models import Asset
from ledger.utils.wallet_pipeline import WalletPipeline
from ledger.utils.withdraw_verify import can_withdraw

logger = logging.getLogger(__name__)

MIN_WITHDRAW = 100_000
MAX_WITHDRAW = 100_000_000


class WithdrawRequestSerializer(serializers.ModelSerializer):
    iban = serializers.CharField(write_only=True)
    code = serializers.CharField(write_only=True)
    code_2fa = serializers.CharField(write_only=True, required=False, allow_blank=True)

    def create(self, validated_data):
        user = self.context['request'].user

        if not can_withdraw(user.account):
            raise ValidationError('در حال حاضر امکان برداشت وجود ندارد.')

        if user.level < user.LEVEL2:
            raise ValidationError('برای برداشت ابتدا احراز هویت نمایید.')

        amount = validated_data['amount']
        iban = validated_data['iban']
        code = validated_data['code']

        bank_account = get_object_or_404(BankAccount, iban=iban, user=user, verified=True, deleted=False)

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

        if is_2fa_active_for_user(user):
            code_2fa = validated_data.get('code_2fa') or ''
            code_2fa_verifier(user_token=user.auth2fa.token, code_2fa=code_2fa)

        if amount < MIN_WITHDRAW:
            logger.info('FiatRequest rejected due to small amount. user=%s' % user.id)
            raise ValidationError({'iban': 'مقدار وارد شده کمتر از حد مجاز است.'})

        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_withdraws = FiatWithdrawRequest.objects.filter(
            bank_account=bank_account,
            created__gte=today,
        ).aggregate(amount=Sum('amount'))['amount'] or 0

        if amount + today_withdraws > MAX_WITHDRAW:
            logger.info('FiatRequest rejected due to large amount. user=%s' % user.id)
            raise ValidationError({'amount': 'حداکثر میزان برداشت به حساب بانکی در روز ۱۰۰ میلیون تومان است.'})

        asset = Asset.get(Asset.IRT)
        wallet = asset.get_wallet(user.account)

        if not wallet.has_balance(amount):
            raise ValidationError({'amount': 'موجودی کافی نیست.'})

        if user_reached_fiat_withdraw_limit(user, amount):
            logger.info('FiatRequest rejected due to max withdraw limit reached. user=%s' % user.id)
            raise ValidationError({'amount': 'شما به سقف برداشت ریالی خود رسیده اید.'})

        # fee_amount = min(4000, int(amount * 0.01))
        fee_amount = 5000
        withdraw_amount = amount - fee_amount

        try:
            with WalletPipeline() as pipeline:  # type: WalletPipeline
                withdraw_request = FiatWithdrawRequest.objects.create(
                    status=FiatWithdrawRequest.INIT,
                    amount=withdraw_amount,
                    fee_amount=fee_amount,
                    bank_account=bank_account,
                    withdraw_channel=config('WITHDRAW_CHANNEL')
                )

                pipeline.new_lock(
                    key=withdraw_request.group_id,
                    wallet=wallet,
                    amount=amount,
                    reason=WalletPipeline.WITHDRAW
                )

        except InsufficientBalance:
            raise ValidationError({'amount': 'موجودی کافی نیست'})

        if otp_code:
            otp_code.set_code_used()

        if auto_verify_fiat_withdraw(withdraw_request) and not settings.DEBUG_OR_TESTING_OR_STAGING:
            withdraw_request.change_status(FiatWithdrawRequest.PROCESSING)
            from financial.tasks import process_withdraw
            process_withdraw.s(withdraw_request.id).apply_async(countdown=FiatWithdrawRequest.FREEZE_TIME)

        return withdraw_request

    class Meta:
        model = FiatWithdrawRequest
        fields = ('iban', 'amount', 'code', 'code_2fa')


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
        return fiat_withdraw_request.receive_datetime

    def get_status(self, withdraw: FiatWithdrawRequest):
        if withdraw.status == FiatWithdrawRequest.INIT:
            return FiatWithdrawRequest.PROCESSING
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
