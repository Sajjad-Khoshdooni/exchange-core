from datetime import timedelta

from django.contrib.auth import login
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from accounts.models import User
from accounts.models.phone_verification import VerificationCode
from accounts.validators import mobile_number_validator, RegexValidator


class InitiateSignupSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)


class InitiateSignupView(APIView):
    permission_classes = []

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': 1})

        serializer = InitiateSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        if User.objects.filter(phone=phone).exists():
            return Response({'msg': 'user exists', 'code': 2})

        VerificationCode.send_otp_code(phone, VerificationCode.SCOPE_VERIFY_PHONE)

        return Response({'msg': 'otp sent', 'code': 0})


class SignupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    token = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def create(self, validated_data):
        token = validated_data.pop('token')
        otp_code = VerificationCode.objects.filter(token=token).first()

        if not otp_code \
                or otp_code.created < timezone.now() - timedelta(hours=1) \
                or User.objects.filter(phone=otp_code.phone).exists():

            raise ValidationError({'token': 'توکن نامعتبر است.'})

        phone = otp_code.phone

        return User.objects.create_user(
            username=phone,
            phone=phone,
            **validated_data
        )


class SignupView(CreateAPIView):
    permission_classes = []
    serializer_class = SignupSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        login(self.request, user)
