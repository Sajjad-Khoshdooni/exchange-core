from uuid import uuid4
from django.test import Client
from django.test import TestCase

from ledger.withdraw import binance
from accounts.models import Account
from ledger.models import Asset, Trx
from ledger.utils.precision import get_presentation_amount
from ledger.utils.test import new_account, new_address_book, generate_otp_code, new_network, new_network_asset
from unittest.mock import patch


class WithdrawTestCase(TestCase):
    def setUp(self):
        self.account = new_account()
        self.user = self.account.user
        self.client = Client()
        self.client.force_login(self.user)
        self.network = new_network()
        self.address_book = new_address_book(account=self.account, network=self.network, asset='USDT')
        self.address_book_without_coin = new_address_book(account=self.account, network=self.network)
        self.usdt = Asset.get(Asset.USDT)
        network_asset = new_network_asset(self.usdt, self.network)

        Trx.transaction(
            group_id=uuid4(),
            sender=self.usdt.get_wallet(Account.system()),
            receiver=self.usdt.get_wallet(self.user.account),
            amount=100000,
            scope=Trx.TRANSFER
        )

    def test_withdraw_without_addressbook(self):
        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'address': '123',
            'coin': 'USDT',
            'network': 'BSC',
            'code': generate_otp_code(self.user, 'withdraw')
        })
        self.assertEqual((get_presentation_amount(resp.data['amount'])), amount)

    def test_withdraw_with_addressbook(self):

        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'code': generate_otp_code(self.user, 'withdraw'),
            'address_book_id': self.address_book.id
        })
        self.assertEqual(resp.status_code, 201)

    def test_withdraw_with_addressbook_without_coin(self):
        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'code': generate_otp_code(self.user, 'withdraw'),
            'address_book_id': self.address_book_without_coin.id
        })
        self.assertEqual(resp.status_code, 400)

    def test_withdraw_with_coin_with_addressbook_without_coin(self):
        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'code': generate_otp_code(self.user, 'withdraw'),
            'coin': 'USDT',
            'address_book_id': self.address_book_without_coin.id
        })
        self.assertEqual(resp.status_code, 201)

    def test_withdraw_with_coin_with_addressbook_with_coin(self):
        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'code': generate_otp_code(self.user, 'withdraw'),
            'coin': 'BTC',
            'address_book_id': self.address_book.id
        })
        self.assertEqual(resp.status_code, 201)
