from django.test import TestCase
from financial.utils.test import new_user, new_bank_card, new_gate_way
from django.test import Client


class DepositFiatTestCase(TestCase):

    def setUp(self) -> None:
        self.user = new_user()
        self.bank_card = new_bank_card(self.user)
        self.gate_way = new_gate_way()
        self.client = Client()
        self.client.force_login(self.user)

    def test_deposit(self):
        resp = self.client.post('/api/v1/finance/payment/request/', {
            'amount': '100000',
            'card_pan': self.bank_card.card_pan
        })
        self.assertEqual(resp.status_code, 201)
