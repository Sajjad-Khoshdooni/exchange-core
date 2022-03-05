from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView

from accounts.models.phone_verification import VerificationCode


class VerifyOTPSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        phone = validated_data['phone']
        code = validated_data['code']
        scope = validated_data['scope']

        otp_code = VerificationCode.get_by_code(
            code=code,
            phone=phone,
            scope=scope
        )

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است.'})

        otp_code.code_used = True
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
    serializer_class = VerifyOTPSerializer


class OTPSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        scope = validated_data['scope']
        user = validated_data['user']

        return VerificationCode.send_otp_code(phone=user.phone, scope=scope)

    class Meta:
        model = VerificationCode
        fields = ('scope', )


class SendOTPView(CreateAPIView):
    serializer_class = OTPSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
