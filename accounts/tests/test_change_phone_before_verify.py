from django.test import TestCase, Client

from accounts.models import *


class ChangePhoneBeforeVerifyTestCAse(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test_man', password="password1234", phone='09305913458')
        self.otp = VerificationCode.send_otp_code(self.user.phone, VerificationCode.SCOPE_CHANGE_PHONE,
                                                  user=self.user)
        self.client = Client()
        self.client.force_login(self.user)

    def test_success_change_phone(self):
        url = '/api/v1/accounts/phone/init/'
        data = {
            "password": str(self.user.password),
            "otp": str(self.otp.code),
            "totp": ""
        }
        resp = self.client.post(url, data=data, content_type='application/json')
        self.assertEqual(resp.status_code, 200)