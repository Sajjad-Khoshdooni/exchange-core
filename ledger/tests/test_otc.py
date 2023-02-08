from django.test import TestCase, Client

from accounts.models import Account
from ledger.models import Asset, OTCRequest, OTCTrade
from ledger.utils.test import new_account, set_price


class OTCTestCase(TestCase):
    def setUp(self):
        self.account = new_account()
        user = self.account.user

        self.client = Client()
        self.client.force_login(user)

        self.usdt = Asset.get(Asset.USDT)
        self.btc = Asset.get('BTC')

        set_price(self.usdt, 30000)  # IRT
        set_price(self.btc, 30000)  # USDT

        self.wallet_usdt = self.usdt.get_wallet(self.account)
        self.wallet_btc = self.btc.get_wallet(self.account)

        self.system_wallet_usdt = self.usdt.get_wallet(Account.system())
        self.system_wallet_btc = self.usdt.get_wallet(Account.system())

    def test_otc_from_amount(self):
        self.wallet_usdt.airdrop(10)

        resp = self.client.post('/api/v1/trade/otc/request/', {
            'from_asset': 'USDT',
            'to_asset': 'BTC',
            'from_amount': 10,
        })
        print(resp.data)
        self.assertEqual(resp.status_code, 201)

        token = resp.data['token']

        resp = self.client.post('/api/v1/trade/otc/', {
            'token': token,
        })

        self.assertEqual(resp.status_code, 201)

        self.wallet_usdt.refresh_from_db()
        self.wallet_btc.refresh_from_db()

        self.assertLess(self.wallet_usdt.balance, 10)
        self.assertEqual(self.wallet_usdt.locked, 0)

        self.assertGreater(self.wallet_btc.balance, 0)
        self.assertEqual(self.wallet_usdt.locked, 0)

        otc_request = OTCRequest.objects.get(token=token)
        otc_trade = otc_request.otctrade
        self.assertEqual(otc_trade.execution_type, OTCTrade.PROVIDER)
