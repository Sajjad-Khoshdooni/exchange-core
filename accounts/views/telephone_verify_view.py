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
    token = serializers.UUIDField(write_only=True, required=True)

    def update(self, user, validated_data):
        token = validated_data.pop('token')

        otp_code = VerificationCode.get_by_token(token, VerificationCode.SCOPE_TELEPHONE)

        if not otp_code:
            raise ValidationError({'token': 'کد نامعتبر است.'})

        otp_code.set_token_used()

        user.telephone_verified = True
        user.telephone = validated_data['telephone']
        user.save()

        return user

    class Meta:
        model = User
        fields = ('token', 'telephone', 'telephone_verified')
        read_only_fields = ('telephone_verified', )
        write_only_fields = ('token', )

        extra_kwargs = {
            'token': {'required': True},
        }


class TelephoneOTPVerifyView(UpdateAPIView):
    serializer_class = TelephoneOTPVerifySerializer

    def get_object(self):
        return self.request.user
