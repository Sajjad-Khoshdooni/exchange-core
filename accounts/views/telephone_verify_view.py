from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import VerificationCode
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
    def create(self, validated_data):
        user = validated_data['user']
        token = validated_data.pop('token')

        otp_code = VerificationCode.get_by_token(token, VerificationCode.SCOPE_TELEPHONE)

        if not otp_code:
            raise ValidationError({'token': 'کد نامعتبر است.'})

        otp_code.set_token_used()

        user.telephone_verified = True
        user.save()

        return otp_code

    class Meta:
        model = VerificationCode
        fields = ('token', 'scope')
        read_only_fields = ('scope', )

        extra_kwargs = {
            'token': {'required': True},
        }


class TelephoneOTPVerifyView(CreateAPIView):
    serializer_class = TelephoneOTPVerifySerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
