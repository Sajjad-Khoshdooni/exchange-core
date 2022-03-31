from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User


class ChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if not data.get('password') == data.get('confirm_password'):
            raise ValidationError('تکرار رمز عبور اشتباه وارد شده است')
        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance


class ChangePasswordView(APIView):
    permission_classes = []

    def put(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        change_password_serializer = ChangePasswordSerializer(
            instance=user,
            data=request.data,
            partial=True
        )
        if change_password_serializer.is_valid():
            change_password_serializer.save()
            return Response({'msg':'pass update successfully'})
        return Response({'message': change_password_serializer.errors})
