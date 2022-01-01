from datetime import timedelta

from django.contrib.auth import login
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from account import codes
from account.models import User
from account.models.phone_verification import VerificationCode
from account.utils import is_phone
from account.validators import mobile_number_validator, RegexValidator, password_validator


class InitiateForgotPasswordSerializer(serializers.Serializer):
    login = serializers.CharField(required=True)

    def create(self, validated_data):
        login_phrase = validated_data['login']
        user = User.get_user_from_login(login_phrase)

        if not user:
            raise ValidationError({'login': 'کاربری یافت نشد.'})

        VerificationCode.send_otp_code(user.phone, VerificationCode.SCOPE_FORGET_PASSWORD)

        return user


class InitiateForgetPasswordView(APIView):
    permission_classes = []

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': codes.USER_ALREADY_LOGGED_IN})

        serializer = InitiateForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({'msg': 'otp sent', 'code': codes.SUCCESS})


class ForgotPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField(write_only=True, required=True)
    password = serializers.CharField(required=True, write_only=True, validators=[password_validator])

    def create(self, validated_data):
        token = validated_data.pop('token')
        otp_code = VerificationCode.get_by_token(token, VerificationCode.SCOPE_FORGET_PASSWORD)

        if not otp_code:
            raise ValidationError({'token': 'توکن نامعتبر است.'})

        user = User.objects.get(phone=otp_code.phone)
        user.set_password(validated_data.pop('password'))
        user.save()

        otp_code.token_used = True
        otp_code.save()

        return user


class ForgetPasswordView(CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = ForgotPasswordSerializer
