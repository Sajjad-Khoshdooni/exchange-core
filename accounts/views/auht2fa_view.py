from django.core.exceptions import ValidationError
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from rest_framework import views
from rest_framework.response import Response

from accounts.models.phone_verification import VerificationCode


class TOTPActivationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)
    sms_code = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        user = self.instance
        token = data.get('token')
        sms_code = data.get('sms_code')

        sms_code = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.SCOPE_2FA_ACTIVATE, user)
        device = TOTPDevice.objects.filter(user=user).first()
        if not sms_code:
            raise ValidationError({'sms_code': 'کد ارسال شده برای فعال سازی ورود دومرحله‌ای نامعتبر است.'})
        if device is None:
            raise ValidationError({'device': 'ابتدا بارکد را دریافت کنید.'})
        if not device.verify_token(token):
            raise ValidationError({'token': 'رمز موقت بدرستی وارد نشده است'})
        return data


class TOTPDeActivationSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)
    sms_code = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        user = self.instance
        token = data.get('token')
        sms_code = data.get('sms_code')

        sms_code = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.SCOPE_2FA_DEACTIVATE, user)
        device = TOTPDevice.objects.filter(user=user).first()
        if not sms_code:
            raise ValidationError({'sms_code': 'کد ارسال شده برای غیرفعال سازی ورود دومرحله‌ای نامعتبر است.'})
        if device is None:
            raise ValidationError({'device': 'ابتدا ورود دومرحله‌ای را فعال کنید.'})
        if not device.verify_token(token):
            raise ValidationError({'token': 'رمز موقت بدرستی وارد نشده است'})
        return data


class TOTPDeActivationView(views.APIView):
    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.filter(user=user)
        if device is None:
            return Response({'msg': 'Your 2fa is not activated'})
        VerificationCode.send_otp_code(phone=user.phone, scope=VerificationCode.SCOPE_2FA_DEACTIVATE, user=user)
        return Response({'msg': 'sms code has been sent'})

    def patch(self, request):
        user = request.user
        totp_de_active_serializer = TOTPDeActivationSerializer(
            instance=user,
            data=request.data,
            partial=True,
            context={
                'request': request
            }
        )
        totp_de_active_serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=user).first()
        device.confirmed = False
        device.save()
        return Response({'msg': '2FA has been deactivated successfully'})


class TOTPActivationView(views.APIView):
    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.filter(user=user).first()
        if device is None:
            device = TOTPDevice.objects.create(user=user, confirmed=False)
        VerificationCode.send_otp_code(phone=user.phone, scope=VerificationCode.SCOPE_2FA_ACTIVATE, user=user)
        return Response(device.config_url)

    def patch(self, request):
        user = request.user
        totp_verify_serializer = TOTPActivationSerializer(
            instance=user,
            data=request.data,
            partial=True,
            context={
                'request': request
            }
        )
        totp_verify_serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=user).first()
        device.confirmed = True
        device.save()
        return Response({'msg': '2FA has been activated successfully'})
