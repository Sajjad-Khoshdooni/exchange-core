from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from django.test import TestCase, Client
from accounts.tasks import verify_user
from accounts.models import User
from financial.utils.test import new_user


class VerificationLevel2TestCase(TestCase):

    def setUp(self):
        # self.user_verify = new_user()
        self.user = new_user(level=User.LEVEL1)
        self.client = Client()

    @patch.object(verify_user, 'basic_verify_user')
    def test_success_verify(self, basic_verify_user):
        basic_verify_user.return_value = 1
        self.client.force_login(self.user)
        resp = self.client.post('/api/v1/accounts/verify/basic/', {
            'first_name': 'علی',
            'last_name': 'صالحی',
            'birth_date': '2000-01-01',
            'national_code': '1230046917',
            'card_pan': '6104337574599260',
            'iban': 'IR369271754583789114976929',
        })
        # self.assertEqual(self.user.verify_status, User.PENDING)
        self.assertEqual(resp.json()['verify_status'], User.PENDING)
