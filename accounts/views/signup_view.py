from accounts.throttle import SustainedRateThrottle, BurstRateThrottle
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.models.phone_verification import VerificationCode
from ledger.models import alert_user_prize
from accounts.validators import mobile_number_validator, password_validator
from ledger.models import Prize, Asset


class InitiateSignupSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)


class InitiateSignupView(APIView):
    permission_classes = []
    throttle_classes = [SustainedRateThrottle, BurstRateThrottle]

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

        user.set_password(password)
        user.save()

        otp_code.set_token_used()
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
