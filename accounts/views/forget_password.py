from django.contrib.auth import login
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView

from accounts import codes
from accounts.models import User
from accounts.models.phone_verification import VerificationCode
from accounts.validators import mobile_number_validator, RegexValidator


class InitiateForgotPasswordSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, validators=[mobile_number_validator], trim_whitespace=True)


class InitiateForgetPasswordView(APIView):
    permission_classes = []

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': codes.USER_ALREADY_LOGGED_IN})

        serializer = InitiateForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone']

        if not User.objects.filter(phone=phone).exists():
            return Response({'msg': 'no match', 'code': codes.FAILED}, status=status.HTTP_400_BAD_REQUEST)

        VerificationCode.send_otp_code(phone, VerificationCode.SCOPE_FORGET_PASSWORD)

        return Response({'msg': 'otp sent', 'code': codes.SUCCESS})


class ForgotPasswordSerializer(serializers.Serializer):
    pass
#     id = serializers.CharField(read_only=True)
#     otp_code = serializers.CharField(write_only=True, required=True, validators=[RegexValidator(r'^\d{6}$')])
#     first_name = serializers.CharField(required=True)
#     last_name = serializers.CharField(required=True)
#     password = serializers.CharField(required=True, write_only=True)
#
#     def create(self, validated_data):
#         otp_code = VerificationCode.get_otp_code(validated_data.pop('otp_code'))
#
#         if not otp_code:
#             raise ValidationError({'otp_code': 'کد نامعتبر است.'})
#
#         phone = otp_code.phone
#
#         otp_code.used = True
#         otp_code.save()
#
#         return User.objects.create_user(
#             username=phone,
#             phone=phone,
#             **validated_data
#         )
#
#
# class SignupView(CreateAPIView):
#     permission_classes = []
#     serializer_class = SignupSerializer
#
#     def perform_create(self, serializer):
#         user = serializer.save()
#         login(self.request, user)
