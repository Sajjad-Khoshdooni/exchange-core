from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User, TrafficSource, Referral
from accounts.models.phone_verification import VerificationCode
from accounts.throttle import BurstRateThrottle
from accounts.validators import mobile_number_validator, password_validator
from ledger.models import Prize, Asset
from ledger.models.prize import alert_user_prize


class InitiateSignupSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)


class InitiateSignupView(APIView):
    permission_classes = []
    throttle_classes = [BurstRateThrottle]

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': 1})

        serializer = InitiateSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        if User.objects.filter(phone=phone).exists():
            raise ValidationError('شماره موبایل وارد شده در سیستم وجود دارد.')

        VerificationCode.send_otp_code(phone, VerificationCode.SCOPE_VERIFY_PHONE)

        return Response({'msg': 'otp sent', 'code': 0})


class SignupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    token = serializers.UUIDField(write_only=True, required=True)
    password = serializers.CharField(required=True, write_only=True, validators=[password_validator])
    utm = serializers.JSONField(allow_null=True, required=False, write_only=True)
    referral_code = serializers.CharField(allow_null=True, required=False, write_only=True)

    @staticmethod
    def validate_referral_code(code):
        if code and not Referral.objects.filter(code=code).exists():
            raise ValidationError(_('Referral code is invalid'))

    def create(self, validated_data):
        token = validated_data.pop('token')
        otp_code = VerificationCode.get_by_token(token, VerificationCode.SCOPE_VERIFY_PHONE)
        password = validated_data.pop('password')

        if not otp_code or User.objects.filter(phone=otp_code.phone).exists():
            raise ValidationError({'token': 'توکن نامعتبر است.'})

        validate_password(password=password)

        phone = otp_code.phone
        otp_code.set_token_used()

        user = User.objects.create_user(
            username=phone,
            phone=phone,
        )

        with transaction.atomic():
            user.set_password(password)
            user.save()
            if validated_data.get('code'):
                user.account.referred_by = Referral.objects.get(code=validated_data['code'])
                user.account.save()

            otp_code.set_token_used()

            utm = validated_data.get('utm') or {}
            utm_source = utm.get('utm_source')

            if utm_source:
                TrafficSource.objects.create(
                    user=user,
                    utm_source=utm_source,
                    utm_medium=utm.get('utm_medium', ''),
                    utm_campaign=utm.get('utm_campaign', ''),
                    utm_content=utm.get('utm_content', ''),
                    utm_term=utm.get('utm_term', ''),
                )

        if Prize.SIGN_UP_PRIZE_ACTIVATE:
            with transaction.atomic():
                prize = Prize.objects.create(
                    account=user.account,
                    amount=Prize.SIGN_UP_PRIZE_AMOUNT,
                    scope=Prize.SIGN_UP_PRIZE,
                    asset=Asset.objects.get(symbol=Asset.SHIB),
                )
                prize.build_trx()
                alert_user_prize(user, prize.scope)

        return user


class SignupView(CreateAPIView):
    permission_classes = []
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
