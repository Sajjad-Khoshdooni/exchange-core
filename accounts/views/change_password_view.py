from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import VerificationCode


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(write_only=True)

    def validate(self, data):

        user = self.instance
        code = data.get('otp_code')
        password = data.get('password')
        old_pass = data.get('old_password')
        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_CHANGE_PASSWORD, user)

        if not user.check_password(old_pass):
            raise ValidationError({'رمز عبور قبلی بدرستی وارد نشده است'})
        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        validate_password(password=password, user=user)

        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance


class ChangePasswordView(APIView):

    def patch(self, request):
        user = self.request.user

        change_password_serializer = ChangePasswordSerializer(
            instance=user,
            data=request.data,
            partial=True,

        )
        change_password_serializer.is_valid(raise_exception=True)

        change_password_serializer.save()
        return Response({'msg': 'password update successfully'})
