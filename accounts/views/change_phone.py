from django.contrib.auth.password_validation import validate_password
from datetime import timedelta
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.tasks import basic_verify_user
from accounts.models import Notification
from accounts.models import User
from accounts.models import VerificationCode
from accounts.utils.notif import send_successful_change_phone_email
from accounts.validators import mobile_number_validator

import logging
logger = logging.getLogger(__name__)


class InitiateChangePhoneSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)
    totp = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        otp = data.get('otp')
        password = data.get('password')
        totp = data.get('totp', None)
        validate_password(password=password, user=user)
        otp_verification = VerificationCode.get_by_code(otp, user.phone, VerificationCode.SCOPE_CHANGE_PHONE_INIT,
                                                        user=user)
        if not otp_verification:
            raise ValidationError('کد ارسال شده نامعتبر است.')

        if not user.is_2fa_valid(totp):
            raise ValidationError({'totp': 'شناسه‌ دوعاملی صحیح نمی‌باشد.'})
        otp_verification.set_code_used()
        data['token'] = otp_verification.token
        return data


class InitiateChangePhone(APIView):
    def post(self, request):
        serializer = InitiateChangePhoneSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response({'token': serializer.validated_data['token']})


class UserVerifySerializer(serializers.Serializer):
    new_phone = serializers.CharField(write_only=True, validators=[mobile_number_validator], trim_whitespace=True)
    token = serializers.CharField(write_only=True)

    def validate(self, data):
        new_phone = data.get('new_phone')
        token = data.get('token')
        token_verification = VerificationCode.get_by_token(token, VerificationCode.SCOPE_CHANGE_PHONE_INIT)
        if not token_verification:
            raise ValidationError('توکن نامعتبر است.')

        token_verification.set_token_used()
        VerificationCode.send_otp_code(new_phone, VerificationCode.SCOPE_NEW_PHONE)
        return data


class NewPhoneVerifySerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)

    def validate(self, data):
        token = data.get('token')
        token_verification = VerificationCode.get_by_token(token, VerificationCode.SCOPE_NEW_PHONE)
        if not token_verification:
            raise ValidationError('توکن نامعتبر است.')

        new_phone = token_verification.phone
        if User.objects.filter(phone=new_phone):
            raise ValidationError(
                'شما با این شماره موبایل قبلا ثبت نام کرده‌اید. لطفا خارج شوید و با این شماره موبایل دوباره وارد شوید.')

        token_verification.set_token_used()
        data['new_phone'] = new_phone
        return data


def send_level_down_message(user: User):
    Notification.send(
        recipient=user,
        title="تغییر سطح کاربری",
        message="سطح کاربری شما به دلیل تغییر شماره تلفن، به سطح 2 کاهش یافت."
    )


class ChangePhoneView(APIView):
    def post(self, request):
        serializer = UserVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'msg': 'کد باموفقیت ارسال شد.'})

    def put(self, request):
        serializer = NewPhoneVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        user.phone = serializer.validated_data['new_phone']
        user.username = user.phone
        new_level = min(user.level, user.LEVEL2)
        if new_level != user.level:
            send_level_down_message(user)

        user.level = new_level
        user.national_code_phone_verified = None

        # user.change_status(User.PENDING)
        # basic_verify_user.delay(user.id)

        user.suspend(timedelta(days=1), 'تغییر شماره‌ تلفن')
        user.save(update_fields=['level', 'national_code_phone_verified', 'phone', 'username'])

        logger.info(f'شماره تلفن همراه {user.get_full_name()}  با‌موفقیت تغییر کرد.')

        send_successful_change_phone_email(user)
        return Response({'msg': 'شماره تلفن همراه با‌موفقیت تغییر کرد.'})
