from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView

from accounts.models.phone_verification import VerificationCode


class OTPSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        phone = validated_data['phone']
        code = validated_data['code']
        scope = validated_data['scope']

        otp_code = VerificationCode.get_otp_code(
            code=code,
            phone=phone,
            scope=scope
        )

        if not otp_code:
            raise ValidationError({'otp_code': 'کد نامعتبر است.'})

        otp_code.used = True
        otp_code.save()

        return otp_code

    class Meta:
        model = VerificationCode
        fields = ('code', 'phone', 'token', 'scope')
        read_only_fields = ('token', )
        extra_kwargs = {
            'code': {'required': True, 'write_only': True},
            'phone': {'write_only': True},
        }


class VerifyOTPView(CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OTPSerializer
