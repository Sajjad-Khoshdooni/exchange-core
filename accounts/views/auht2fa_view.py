from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import views
from rest_framework import serializers
from accounts.models.phone_verification import VerificationCode
class TOTPVerifySerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True, required=True)
    sms_code = serializers.CharField(write_only=True, required=True)

class TOTPCreateView(views.APIView):

    def post(self, request):
        user = request.user
        device = TOTPDevice.objects.get(user=user)
        if device is None:
            device = TOTPDevice.objects.create(user=user, confirmed=False)
        VerificationCode.send_otp_code(user.phone, VerificationCode.SCOPE_2FA_ACTIVATE)
        return device.config_url()


class TOTPVerifyView(views.APIView):
    def post(self, request, token, sms):
        user = request.user
        device = TOTPDevice.objects.get(user)
        if device is not None and device.verify_token(token):
            if not device.confirmed:
                device.confirmed = True
                device.save()
