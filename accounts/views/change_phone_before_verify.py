from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from accounts.models import VerificationCode
from accounts.models import User
from accounts.validators import mobile_number_validator


class ChangePhoneSerializer(serializers.ModelSerializer):
    new_phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)
    otp_code = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.instance
        new_phone = data.get('new_phone')
        code = data.get('otp_code')
        otp_code = VerificationCode.get_by_code(code, new_phone, VerificationCode.SCOPE_CHANGE_PHONE)

        if user.national_code_verified:
            raise ValidationError({'با توجه به تایید کد ملی امکان تغییر شماره وجود ندارد.'})

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        if User.objects.filter(phone=new_phone):
            raise ValidationError({'کاربری با این شماره همراه قبلا ثبت نام کرده است.'})
        return data

    def update(self, instance, validated_data):
        instance.phone = validated_data['new_phone']
        instance.username = validated_data['new_phone']
        instance.save()
        return instance

    class Meta:
        model = User
        fields = ('new_phone', 'otp_code',)


class ChangePhoneView(APIView):

    def patch(self, request):

        user = self.request.user
        change_phone = ChangePhoneSerializer(
            instance=user,
            data=request.data,
            partial=True
        )

        change_phone.is_valid(raise_exception=True)
        change_phone.save()
        return Response({'msg': 'phone change successfully'})
