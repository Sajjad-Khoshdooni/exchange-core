from django_otp.plugins.otp_totp.models import TOTPDevice, default_key
from rest_framework import views
from rest_framework import serializers
from accounts.models.phone_verification import VerificationCode
from django.core.exceptions import ValidationError
from rest_framework.response import Response


class TOTPSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)
    sms_code = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        user = self.instance
        token = data.get('token')
        sms_code = data.get('sms_code')
        sms_code = VerificationCode.get_by_code(sms_code, user.phone, VerificationCode.SCOPE_CHANGE_PASSWORD, user)
        device = TOTPDevice.objects.get(user)
        if not sms_code:
            raise ValidationError({'sms_code': 'کد نامعتبر است.'})
        if device is None:
            raise ValidationError({'device': 'ابتدا بارکد را دریافت کنید.'})
        if not device.verify_token(token):
            raise ValidationError({'token': 'رمز موقت بدرستی وارد نشده است'})
        return data


class TOTPDeleteView(views.APIView):
    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.get(user=user)
        if device is None:
            return Response({'msg': 'Your 2fa is not activated'})
        VerificationCode.send_otp_code(user.phone, VerificationCode.SCOPE_2FA_DEACTIVATE)

    def delete(self, request):
        user = request.user
        totp_verify_serializer = TOTPSerializer(
            instance=user,
            data=request.data,
            partial=True,
            context={
                'request': request
            }
        )
        totp_verify_serializer.is_valid(raise_exception=True)
        totp_verify_serializer.save()
        device = TOTPDevice.objects.get(user)
        device.confirmed = False
        device.key = default_key()


class TOTPActivationView(views.APIView):
    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.get(user=user)
        if device is None:
            device = TOTPDevice.objects.create(user=user, confirmed=False)
        VerificationCode.send_otp_code(user.phone, VerificationCode.SCOPE_2FA_ACTIVATE)
        return device.config_url()

    def patch(self, request):
        user = request.user
        totp_verify_serializer = TOTPSerializer(
            instance=user,
            data=request.data,
            partial=True,
            context={
                'request': request
            }
        )
        totp_verify_serializer.is_valid(raise_exception=True)
        TOTPDevice.objects.get(user).confirmed = True
        return Response({'msg': '2FA has been activated successfully'})
