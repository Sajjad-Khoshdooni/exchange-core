from decimal import Decimal

from django.test import Client
from django.test import TestCase

from ledger.models import Asset
from ledger.utils.test import new_account


class ConvertDustTestCase(TestCase):

    def setUp(self) -> None:
        self.account = new_account()
        user = self.account.user

        self.client = Client()
        self.client.force_login(user)

        self.btc = Asset.get('BTC')
        self.usdt = Asset.get('USDT')
        self.ada = Asset.get('ADA')
        self.irt = Asset.get('IRT')

        self.wallet_usdt = self.usdt.get_wallet(self.account)
        self.wallet_btc = self.btc.get_wallet(self.account)
        self.wallet_ada = self.ada.get_wallet(self.account)
        self.wallet_irt = self.irt.get_wallet(self.account)

    def test_convert_dust_for_zero_wallet(self):
        resp = self.client.post('/api/v1/convert/dust/')

        self.wallet_ada.refresh_from_db()
        self.wallet_btc.refresh_from_db()
        self.wallet_usdt.refresh_from_db()
        self.wallet_irt.refresh_from_db()

        self.assertEqual(resp.status_code, 200)

        self.assertEqual(self.wallet_irt.balance, 0)
        self.assertEqual(self.wallet_ada.balance, 0)
        self.assertEqual(self.wallet_btc.balance, 0)
        self.assertEqual(self.wallet_usdt.balance, 0)

    def test_test_convert_dust(self):
        self.wallet_btc.airdrop(Decimal('.000001'))
        self.wallet_usdt.airdrop(Decimal('10'))

        print('btc balance before dust is {}'.format(self.wallet_btc.balance))
        print('usdt balance before dust is {}'.format(self.wallet_usdt.balance))

        resp = self.client.post('/api/v1/convert/dust/')

        self.wallet_btc.refresh_from_db()
        self.wallet_usdt.refresh_from_db()
        self.wallet_irt.refresh_from_db()

        print('irt{}'.format(self.wallet_irt.balance))
        print('btc{}'.format(self.wallet_btc.balance))
        print('usdt{}'.format(self.wallet_usdt.balance))

        self.assertEqual(resp.status_code, 200)
        self.assertGreater(self.wallet_irt.balance, 0)
        self.assertEqual(self.wallet_usdt.balance, 10)
        self.assertEqual(self.wallet_btc.balance, 0)




