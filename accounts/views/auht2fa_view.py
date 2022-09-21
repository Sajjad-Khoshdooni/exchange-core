import uuid

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView
# class Create2Qrcode(serializers.ModelSerializer):
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import Notification
from accounts.models.auth2fa import Auth2Fa
from accounts.utils import email
from accounts.utils.email import SCOPE_MARGIN_LIQUIDATION_FINISHED, SCOPE_2FA_ACTIVATE
from accounts.utils.auth2fa import create_qr_code, code_2fa_verifier


class Verify2FaSerializer(serializers.Serializer):
    code_2fa = serializers.CharField(write_only=True)

    def save(self, **kwargs):
        user = self.instance
        code_2fa = self.validated_data['code_2fa']
        code_2fa_verifier(user_token=str(user.auth2fa.token), code_2fa=code_2fa)
        auth2fa = user.auth2fa
        auth2fa.verified = True
        auth2fa.save()


class Create2FaQrCodeAPIView(APIView):

    def post(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'auth2fa', None):
            raise ValidationError('این کاربر قبلا qrcode ساخته است')

        token = uuid.uuid4()
        Auth2Fa.objects.create(
            user=user,
            token=token,
            qrcode=create_qr_code(str(token))
        )
        return Response({'qrcode_link': '', })


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
