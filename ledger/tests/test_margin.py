from decimal import Decimal
from unittest import mock

from django.test import TestCase

from django.test import Client
from django.utils import timezone

from ledger.models import Asset, Wallet, OTCRequest, OTCTrade
from ledger.tasks import check_margin_level
from ledger.utils.price import get_tether_irt_price
from ledger.utils.test import new_account, new_trx, set_price


USDT_IRT_PRICE = 20000
XRP_USDT_PRICE = 2

TO_TRANSFER_USDT = 100

class MarginTestCase(TestCase):

    def setUp(self) -> None:
        self.account = new_account()
        self.user = self.account.user
        self.usdt = Asset.get(Asset.USDT)
        self.xrp = Asset.get('XRP')
        new_trx(self.account, self.usdt, TO_TRANSFER_USDT)

        self.client = Client()
        self.client.force_login(self.user)

        set_price(self.usdt, USDT_IRT_PRICE)
        set_price(self.xrp, XRP_USDT_PRICE)

    def get_margin_info(self):
        resp = self.client.get('/api/v1/margin/info/')
        self.assertEqual(resp.status_code, 200)

        return resp.data

    def assert_margin_info(self, total_equity=None, total_debt=None, total_assets=None, margin_level=None):
        info = self.get_margin_info()

        if total_equity is not None:
            self.assertEqual(info['total_equity'], total_equity)

        if total_debt is not None:
            self.assertEqual(info['total_debt'], total_debt)

        if total_assets is not None:
            self.assertEqual(info['total_assets'], total_assets)

        if margin_level is not None:
            self.assertEqual(info['margin_level'], margin_level)

    def transfer(self, amount, type: str = 'sm', check_status=201):
        resp = self.client.post('/api/v1/margin/transfer/', {
            'amount': amount,
            'type': type
        })

        self.assertEqual(resp.status_code, check_status)

    def loan(self, coin: str, amount, type: str = 'borrow', check_status=201):
        resp = self.client.post('/api/v1/margin/loan/', {
            'amount': amount,
            'type': type,
            'coin': coin,
        })

        self.assertEqual(resp.status_code, check_status)

        if check_status == 201:
            self.assertEqual(resp.data['status'], 'done')

    def pass_quiz(self):
        self.user.margin_quiz_pass_date = timezone.now()
        self.user.save()

    def test_transfer(self):
        self.assert_margin_info(0, 0, 0, 999)

        self.transfer(TO_TRANSFER_USDT * 2, check_status=400)
        self.assert_margin_info(0, 0, 0, 999)

        self.transfer(TO_TRANSFER_USDT)

        spot_wallet = self.usdt.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = self.usdt.get_wallet(self.account, Wallet.MARGIN)

        self.assertEqual(spot_wallet.get_balance(), 0)
        self.assertEqual(margin_wallet.get_free(), TO_TRANSFER_USDT)

        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.transfer(2 * TO_TRANSFER_USDT, type='ms', check_status=400)
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.transfer(TO_TRANSFER_USDT, type='ms')
        self.assert_margin_info(0, 0, 0, 999)

    def test_loan(self):
        self.transfer(TO_TRANSFER_USDT)
        self.loan('XRP', TO_TRANSFER_USDT / XRP_USDT_PRICE, check_status=400)

        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.pass_quiz()

        self.loan('XRP', TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assert_margin_info(TO_TRANSFER_USDT, TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 2)

        self.loan('XRP', TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))

        self.loan('XRP', TO_TRANSFER_USDT / XRP_USDT_PRICE, check_status=400)

        self.loan('XRP', 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE, type='repay')
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.loan('XRP', 1, type='repay', check_status=400)
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

    def print_wallets(self, account=None):
        wallets = Wallet.objects.all()

        if account:
            wallets = wallets.filter(account=account)

        for w in wallets:
            print('%s %s %s: %s' % (w.account, w.asset.symbol, w.market, w.get_free()))

        print()

    @mock.patch('ledger.tasks.margin.warn_risky_level')
    def test_liquidate1(self, warn_risky_level):
        self.assertEqual(check_margin_level(), 0)

        self.pass_quiz()
        self.transfer(TO_TRANSFER_USDT)

        self.assertEqual(check_margin_level(), 0)

        self.loan('XRP', 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assertEqual(check_margin_level(), 0)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))

        set_price(self.xrp, XRP_USDT_PRICE * 2)
        self.assertEqual(check_margin_level(), 1)

        warn_risky_level.assert_called_once()
        self.assert_margin_info(TO_TRANSFER_USDT, 4 * TO_TRANSFER_USDT, 5 * TO_TRANSFER_USDT, Decimal('1.25'))

        set_price(self.xrp, XRP_USDT_PRICE * 5)
        self.assertEqual(check_margin_level(), 2)

        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('1.5'))

    def test_liquidate2(self):
        self.pass_quiz()
        self.transfer(TO_TRANSFER_USDT)
        self.loan('USDT', 2 * TO_TRANSFER_USDT)

        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.usdt,
            to_asset=self.xrp,
            from_amount=Decimal(3 * TO_TRANSFER_USDT),
            allow_small_trades=True
        )

        OTCTrade.execute_trade(otc_request)

        self.print_wallets(self.account)

        self.assertEqual(check_margin_level(), 0)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('1.4'))

        set_price(self.xrp, XRP_USDT_PRICE * 2)

        self.assertEqual(check_margin_level(), 0)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2.9'))

        set_price(self.xrp, XRP_USDT_PRICE * 0.7)

        self.assertEqual(check_margin_level(), 2)

        self.print_wallets(self.account)
        self.assertLessEqual(self.get_margin_info()['margin_level'], Decimal('1.45'))
