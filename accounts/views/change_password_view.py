from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import VerificationCode
from accounts.models import User


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    otp_code = serializers.CharField(write_only=True)

    def validate(self, data):

        user = self.context['request'].user
        code = data.get['opt_code']
        otp_code = VerificationCode.get_by_code(code, user.phone, VerificationCode.SCOPE_CHANGE_PASSWORD, user)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})
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
            partial=True
        )
        if change_password_serializer.is_valid():
            change_password_serializer.save(raise_exception=True)
            return Response({'msg': 'password update successfully'})

