import os
import uuid

from django.conf import settings
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Notification, VerificationCode
from accounts.models.auth2fa import Auth2Fa
from accounts.utils import email
from accounts.utils.auth2fa import create_qr_code, code_2fa_verifier, is_2fa_active_for_user
from accounts.utils.email import SCOPE_2FA_ACTIVATE


class Verify2FaSerializer(serializers.Serializer):
    code_2fa = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.instance
        code_2fa = attrs['code_2fa']
        otp = attrs['otp']
        code_2fa_verifier(user_token=str(user.auth2fa.token), code_2fa=code_2fa)
        otp_code = VerificationCode.get_by_code(otp, user.phone, VerificationCode.SCOPE_2FA_ACTIVATE)

        if not otp_code:
            raise ValidationError({'code': 'کد نامعتبر است'})
        otp_code.set_code_used()
        return attrs

    def save(self, **kwargs):
        user = self.instance
        auth2fa = user.auth2fa
        qr_path = settings.MEDIA_ROOT + auth2fa.qrcode
        if os.path.isfile(qr_path):
            os.remove(qr_path)
        auth2fa.qrcode = ''
        auth2fa.verified = True
        auth2fa.save()


class Create2FaQrCodeAPIView(APIView):

    def post(self, request, *args, **kwargs):
        user = request.user

        if getattr(user, 'auth2fa', None):
            raise ValidationError('این کاربر قبلا qrcode ساخته است')

        qrcode_address = create_qr_code(str(token))
        Auth2Fa.objects.create(
            user=user,
            token=token,
            qrcode=qrcode_address
        )
        return Response({'qrcode_link': settings.MINIO_STORAGE_MEDIA_URL + qrcode_address})

    def delete(self, request, *args, **kwargs):
        user = request.user
        if not is_2fa_active_for_user(user):
            raise ValidationError('رمز دوعاملی برای شما فعال نیست.')

        verify_2fa_serializer = Verify2FaSerializer(data=request.data, instance=user)
        verify_2fa_serializer.is_valid(raise_exception=True)

        user.auth2fa.delete()
        return Response({'msg': 'رمز دو عاملی شما حذف شد.'})


class Verify2FaVerificationAPIView(APIView):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        if not getattr(user, 'auth2fa', None):
            raise ValidationError('این کاربر قبلا qrcode نساخته است')

        verify_2fa_serializer = Verify2FaSerializer(data=request.data, instance=user)
        verify_2fa_serializer.is_valid(raise_exception=True)

        verify_2fa_serializer.save()
        try:
            Notification.send(
                recipient=user,
                title='فعال کردن رمز دوعاملی',
                level=Notification.SUCCESS,
                message='رمز دوعاملی شما با موفقیت فعال شد.',
            )
            if user.email:
                email.send_email_by_template(
                    recipient=user.email,
                    template=SCOPE_2FA_ACTIVATE,
                )

        except:
            pass

        return Response({'msg': 'رمز دوعاملی برای شما فعال شد.'})
