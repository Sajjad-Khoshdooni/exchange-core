from django.core.exceptions import ValidationError
from django_otp.plugins.otp_totp.models import TOTPDevice, default_key
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models.phone_verification import VerificationCode
from accounts.utils.notif import send_2fa_deactivation_message, send_2fa_activation_message


class TOTPSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    sms_code = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        token = data.get('token')
        sms_code = data.get('sms_code')
        sms_verification_code = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.SCOPE_2FA, user)
        if not sms_verification_code:
            raise ValidationError({'sms_code': 'کد ارسال شده برای فعال سازی ورود دومرحله‌ای نامعتبر است.'})
        sms_verification_code.set_code_used()
        device = TOTPDevice.objects.filter(user=user).first()
        if device is None:
            raise ValidationError({'device': 'ابتدا بارکد را دریافت کنید.'})
        if not device.verify_token(token):
            raise ValidationError({'token': 'رمز موقت صحیح نمی‌باشد.'})
        return data


class TOTPView(APIView):

    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.filter(user=user).first()
        VerificationCode.send_otp_code(phone=user.phone, scope=VerificationCode.SCOPE_2FA, user=user)
        if device is None:
            device = TOTPDevice.objects.create(user=user, confirmed=False)
        if device.confirmed is False:
            device.key = default_key()
            device.save(update_fields=['key'])
            return Response(device.config_url)
        else:
            return Response({'msg': 'پیامک با موفقیت ارسال شد.'})

    def put(self, request):
        user = request.user
        totp_verify_serializer = TOTPSerializer(
            data=request.data,
            context={
                'request': request
            }
        )
        totp_verify_serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=user).first()
        if not device.confirmed:
            device.confirmed = True
            device.save(update_fields=['confirmed'])
            send_2fa_activation_message(user=user)
            return Response({'msg': 'ورود دومرحله‌ای باموفقیت برای حساب کاربری فعال شد.'})
        else:
            return Response({'msg': 'ورود دو مرحله‌ای فعال می باشد.'})

    def delete(self, request):
        user = request.user
        totp_de_active_serializer = TOTPSerializer(
            data=request.data,
            context={
                'request': request
            }
        )
        totp_de_active_serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=user).first()
        if device.confirmed:
            device.confirmed = False
            device.save(update_fields=['confirmed'])
            send_2fa_deactivation_message(user=user)
            return Response({'msg': 'ورود دومرحله‌ای باموفقیت برای حساب کاربری غیرفعال شد.'})
        else:
            return Response({'msg' : 'ورود دومرحله‌ای غیرفعال است.'})