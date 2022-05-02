from rest_framework import serializers

from accounts.throttle import BurstRateThrottle, SustainedRateThrottle
from accounts.validators import email_validator
from rest_framework.views import APIView
from rest_framework.generics import UpdateAPIView
from accounts.models import User
from rest_framework.exceptions import ValidationError
from accounts.models import EmailVerificationCode
from rest_framework.response import Response


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, validators=[email_validator], trim_whitespace=True)


class EmailVerifyView(APIView):
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = self.request.user
        if User.objects.filter(email=email).exists():
            raise ValidationError('ایمیل وارد شده در سیستم وجود دارد.')

        EmailVerificationCode.send_otp_code(email, EmailVerificationCode.SCOPE_VERIFY_EMAIL, user)

        return Response({'msg': 'otp send', 'code': 0})


class EmailOTPVerifySerializer(serializers.ModelSerializer):

    code = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('code', 'email')
        read_only_fields = ('email', )
        extra_kwargs = {
            'email': {'required': True},
        }

    def update(self, user, validated_data):
        code = validated_data.get('code')

        otp_code = EmailVerificationCode.get_by_code(code, user, EmailVerificationCode.SCOPE_VERIFY_EMAIL)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است'})

        otp_code.set_code_used()

        user.email = otp_code.email
        user.save()

        return user


class EmailOTPVerifyView(UpdateAPIView):
    serializer_class = EmailOTPVerifySerializer
    throttle_classes = [BurstRateThrottle, SustainedRateThrottle]

    def get_object(self):
        return self.request.user
