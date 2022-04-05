from django.contrib.auth import login
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.throttle import SustainedRateThrottle,BurstRateThrottle
from accounts.models import User
from accounts.models.phone_verification import VerificationCode
from accounts.validators import mobile_number_validator, password_validator
from django.contrib.auth.password_validation import validate_password

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

        return user


class SignupView(CreateAPIView):
    permission_classes = []
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
