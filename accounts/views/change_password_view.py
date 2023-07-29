from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django_otp.plugins.otp_totp.models import TOTPDevice

from accounts.models import VerificationCode


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(write_only=True)
    totp = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    def validate(self, data):
        # todo : test
        user = self.context['request'].user
        code = data.get('otp_code')
        password = data.get('password')
        old_pass = data.get('old_password')
        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_CHANGE_PASSWORD, user)
        totp = data.get('totp')
        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})
        otp_code.set_code_used()
        if not user.check_password(old_pass):
            raise ValidationError({'old_password': 'رمز عبور قبلی بدرستی وارد نشده است'})
        device = TOTPDevice.objects.filter(user=user).first()
        if not (device is None or not device.confirmed or device.verify_token(totp)):
            raise ValidationError({'totp': ' رمز موقت نامعتبر است.'})
        validate_password(password=password, user=user)

        return data

    def update(self, user, validated_data):
        user.set_password(validated_data['password'])
        user.save()

        request = self.context['request']
        login(request, user)

        return user


class ChangePasswordView(APIView):
    def patch(self, request):
        user = self.request.user

        change_password_serializer = ChangePasswordSerializer(
            instance=user,
            data=request.data,
            partial=True,
            context={
                'request': request
            }
        )
        change_password_serializer.is_valid(raise_exception=True)

        change_password_serializer.save()
        return Response({'msg': 'password update successfully'})
