from django.core.exceptions import ValidationError
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from rest_framework import views
from rest_framework.response import Response
from accounts.utils.notif import send_2fa_deactivation_message, send_2fa_activation_message
from accounts.models.phone_verification import VerificationCode


class TOTPSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)
    sms_code = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        user = self.context['request'].user
        token = data.get('token')
        sms_code = data.get('sms_code')
        sms_code = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.SCOPE_2FA, user)
        device = TOTPDevice.objects.filter(user=user).first()
        if not sms_code:
            raise ValidationError({'sms_code': 'کد ارسال شده برای فعال سازی ورود دومرحله‌ای نامعتبر است.'})
        if device is None:
            raise ValidationError({'device': 'ابتدا بارکد را دریافت کنید.'})
        if not device.verify_token(token):
            raise ValidationError({'token': 'رمز موقت صحیح نمی‌باشد.'})
        return data


class TOTPView(views.APIView):
    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.filter(user=user).first()
        VerificationCode.send_otp_code(phone=user.phone, scope=VerificationCode.SCOPE_2FA, user=user)
        if device is None:
            device = TOTPDevice.objects.create(user=user, confirmed=False)
        if device.confirmed is False:
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
        device.confirmed = True
        device.save(update_fields=['confirmed'])
        send_2fa_activation_message(user=user)
        return Response({'msg': 'ورود دومرحله‌ای باموفقیت برای حساب کاربری فعال شد.'})

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
        device.confirmed = False
        device.save(update_fields=['confirmed'])
        send_2fa_deactivation_message(user=user)
        return Response({'msg': 'ورود دومرحله‌ای باموفقیت برای حساب کاربری غیرفعال شد.'})
