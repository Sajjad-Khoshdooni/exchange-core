from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import VerificationCode, User
from accounts.validators import telephone_number_validator


class InitiateTelephoneSerializer(serializers.Serializer):
    telephone = serializers.CharField(required=True, validators=[telephone_number_validator], trim_whitespace=True)


class InitiateTelephoneVerifyView(APIView):

    def post(self, request):
        serializer = InitiateTelephoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telephone = serializer.validated_data['telephone']

        user = request.user

        if user.telephone_verified:
            raise ValidationError('شماره تلفن تایید شده است.')

        VerificationCode.send_otp_code(telephone, VerificationCode.SCOPE_TELEPHONE)

        return Response({'msg': 'otp sent', 'code': 0})


class TelephoneOTPVerifySerializer(serializers.ModelSerializer):
    code = serializers.CharField(write_only=True, required=True)

    def update(self, user, validated_data):
        code = validated_data['code']

        otp_code = VerificationCode.get_by_code(code, user.telephone, VerificationCode.SCOPE_TELEPHONE)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        otp_code.set_code_used()

        user.telephone_verified = True
        user.telephone = validated_data['telephone']
        user.save()

        return user

    class Meta:
        model = User
        fields = ('code', 'telephone', 'telephone_verified')
        read_only_fields = ('telephone_verified', )


class TelephoneOTPVerifyView(UpdateAPIView):
    serializer_class = TelephoneOTPVerifySerializer

    def get_object(self):
        return self.request.user
