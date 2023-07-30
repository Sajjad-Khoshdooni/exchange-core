from django.contrib.auth.password_validation import validate_password
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import VerificationCode
from accounts.validators import mobile_number_validator


class InitiateChangePhoneSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)
    totp = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        otp = data.get('otp')
        password = data.get('password')
        totp = data.get('totp')
        validate_password(password=password, user=user)
        otp_verification = VerificationCode.get_by_code(otp, user.phone, VerificationCode.SCOPE_CHANGE_PHONE, user)
        if not otp_verification:
            raise ValidationError('کد ارسال شده نامعتبر است.')
        otp_verification.set_code_used()
        device = TOTPDevice.objects.filter(user=user).first()
        if not (not device or not device.confimed or device.verify_token(totp)):
            raise ValidationError('رمز موقت نامعتبر است.')
        data['token'] = otp_verification.token
        return data


class InitiateChangePhone(APIView):
    def post(self, request):
        serializer = InitiateChangePhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data['token'])


class ChangePhonePostSerializer(serializers.ModelSerializer):
    new_phone = serializers.CharField(write_only=True, validators=[mobile_number_validator], trim_whitespace=True)
    token = serializers.CharField(write_only=True)

    def validate(self, data):
        new_phone = data.get('new_phone')
        token = data.get('token')
        token_verification = VerificationCode.get_by_token(token, VerificationCode.SCOPE_CHANGE_PHONE)
        if not token_verification:
            raise ValidationError('توکن نامعتبر است.')
        token_verification.set_token_used()
        VerificationCode.send_otp_code(new_phone, VerificationCode.SCOPE_CHANGE_PHONE)


class ChangePhonePutSerializer(serializers.ModelSerializer):
    token = serializers.CharField(write_only=True)

    def validate(self, data):
        token = data.get('token')
        token_verification = VerificationCode.get_by_token(token, VerificationCode.SCOPE_CHANGE_PHONE)
        if not token_verification:
            raise ValidationError('توکن نامعتبر است.')
        token_verification.set_token_used()
        data['new_phone'] = token_verification.phone
        return data


class ChangePhoneView(APIView):
    def post(self, request):
        serializer = ChangePhonePostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({'msg': 'کد باموفقیت ارسال شد.'})

    def put(self, request):
        serializer = ChangePhonePutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.phone = serializer.validated_data['new_phone']
        user.username = user.phone
        user.level = max(user.level, user.LEVEL2)
        user.save()
        return Response(serializer.validated_data['token'])
