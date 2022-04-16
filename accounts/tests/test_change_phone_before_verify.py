from django.test import TestCase, Client
from accounts.models import User
from financial.utils.test import new_user
from accounts.utils.test import generate_otp_code


class ChangePhoneBeforeVerifyTestCAse(TestCase):

    def setUp(self):
        self.user_1 = new_user(name='test_user_1', phone='09305913458', level=User.LEVEL1)
        self.client = Client()
        self.client.force_login(self.user_1)

    def test_success_change_phone(self):
        code = generate_otp_code(scope='change_phone', phone='09315913458', user=self.user_1)
        resp = self.client.patch('/api/v1/accounts/phone/change/', {
            "new_phone": "09315913458",
            "otp_code": code,
        }, content_type='application/json')
        print(resp.data)
        self.assertEqual(resp.status_code, 200)

    def test_user_verify_national_code(self):
        self.user_1.national_code_verified = True
        self.user_1.save()
        code = generate_otp_code(scope='change_phone', phone='09315913458', user=self.user_1)
        resp = self.client.patch('/api/v1/accounts/phone/change/', {
            "new_phone": "09315913458",
            "otp_code": code,
        }, content_type='application/json')
        print(self.user_1.national_code_verified)
        self.assertEqual(resp.status_code, 400)
