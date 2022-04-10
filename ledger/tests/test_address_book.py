from uuid import uuid4

from django.test import TestCase
from ledger.utils.precision import get_presentation_amount
from accounts.models import Account
from ledger.models import AddressBook, Asset, Trx
from ledger.utils.test import new_account, new_address_book, generate_otp_code, new_network, new_network_asset
from django.test import Client


class AddressBookTestCase(TestCase):

    def setUp(self):
        self.account = new_account()
        self.user = self.account.user
        self.user.telephone = '09355913457'
        self.client = Client()
        self.client.force_login(self.user)
        self.network = new_network()
        self.address_book = new_address_book(name='test1', address='asdfs12', network=self.network, asset='USDT')
        self.usdt = Asset.get(Asset.USDT)
        network_asset = new_network_asset(self.usdt, self.network)

        Trx.transaction(
            group_id=uuid4(),
            sender=self.usdt.get_wallet(Account.system()),
            receiver=self.usdt.get_wallet(self.user.account),
            amount=100000,
            scope=Trx.TRANSFER
        )
    # def test_str(self):
    #     address_book = AddressBook.objects.get(name='test1')
    #     self.assertEqual(address_book.__str__(), 'test1')

    # def test_list_address_book(self):
    #     resp = self.client.get('/api/v1/addressbook/')
    #     self.assertEqual(resp.status_code, 200)

    # def test_create_address_book(self):
    #     pass
    #
    # def test_update_address_book(self):
    #     pass
    #
    # def test_delete_address_book(self):
    #     pass
    # #
    # # def test_withdraw_1(self):
    # #     resp = self.client.post('/api/v1/withdraw/')
    # #     self.assertEqual(resp.status_code, 400)

    def test_withdraw_2(self):
        amount = '50'
        resp = self.client.post('/api/v1/withdraw/', {
            'amount': amount,
            'address': 'asdf',
            'coin': 'USDT',
            'network': 'BSC',
            'code': generate_otp_code(self.user, 'withdraw')
        })
        self.assertEqual((get_presentation_amount(resp.data['amount'])), (amount) )
