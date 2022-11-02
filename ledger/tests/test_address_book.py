from django.test import Client
from django.test import TestCase
from ledger.models import Asset
from ledger.utils.test import new_account, new_address_book, new_network, new_network_asset


class AddressBookTestCase(TestCase):

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

    def test_create_address_book(self):
        resp = self.client.post('/api/v1/addressbook/', {
            'name': 'test_addressbook',
            'network': 'BSC',
            'coin': 'USDT',
            'address': 'test'
        })
        self.assertEqual(resp.status_code, 400)

    def test_list_address_book(self):
        resp = self.client.get('/api/v1/addressbook/')
        self.assertEqual(len(resp.data['results']), 2)
        self.assertEqual(resp.status_code, 200)

    def test_delete_address_book(self):
        resp = self.client.delete('/api/v1/addressbook/{}/'.format(self.address_book.pk))
        self.assertEqual(resp.status_code, 204)
