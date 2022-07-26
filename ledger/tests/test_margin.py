from decimal import Decimal
from unittest import mock

from django.test import Client
from django.test import TestCase
from django.utils import timezone

from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT
from ledger.models import Asset, Wallet, OTCRequest, OTCTrade, Trx
from ledger.tasks import check_margin_level
from ledger.utils.price import BUY
from ledger.utils.test import new_account, set_price
from market.models import PairSymbol
from market.utils import new_order

USDT_IRT_PRICE = 20000
XRP_USDT_PRICE = 2
BTC_USDT_PRICE = Decimal(1000)

TO_TRANSFER_USDT = 100


class MarginTestCase(TestCase):

    def setUp(self) -> None:
        self.account = new_account()
        self.user = self.account.user
        self.user.show_margin = True
        self.user.save()
        self.usdt = Asset.get(Asset.USDT)
        self.usdt.margin_enable = True
        self.usdt.save()

        self.xrp = Asset.get('ADA')
        self.xrp.margin_enable = True
        self.xrp.save()

        self.btc = Asset.get('BTC')
        self.btc.margin_enable = True
        self.btc.save()

        self.usdt.get_wallet(self.account).airdrop(TO_TRANSFER_USDT)

        self.client = Client()
        self.client.force_login(self.user)

        set_price(self.usdt, USDT_IRT_PRICE)
        set_price(self.xrp, XRP_USDT_PRICE)
        set_price(self.btc, int(BTC_USDT_PRICE))

        self.btcusdt = PairSymbol.objects.get(name='BTCUSDT')

        self.xrpusdt = PairSymbol.objects.get(name='ADAUSDT')
        self.xrpusdt.taker_fee = 0
        self.xrpusdt.save()

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

    def transfer_usdt(self, amount, type: str = 'sm', check_status=201):
        resp = self.client.post('/api/v1/margin/transfer/', {
            'amount': amount,
            'type': type,
            'coin': 'USDT'
        })
        print(resp.data)
        print(Asset.get('USDT').margin_enable, self.user.show_margin)
        self.assertEqual(resp.status_code, check_status)

    def transfer_xrp(self, amount, type: str = 'sm', check_status=201):
        resp = self.client.post('/api/v1/margin/transfer/', {
            'amount': amount,
            'type': type,
            'coin': 'ADA'
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
        self.pass_quiz()

        self.assert_margin_info(0, 0, 0, 999)

        self.transfer_usdt(TO_TRANSFER_USDT * 2, check_status=400)
        self.assert_margin_info(0, 0, 0, 999)

        self.transfer_usdt(TO_TRANSFER_USDT)

        spot_wallet = self.usdt.get_wallet(self.account, Wallet.SPOT)
        margin_wallet = self.usdt.get_wallet(self.account, Wallet.MARGIN)

        self.assertEqual(spot_wallet.get_balance(), 0)
        self.assertEqual(margin_wallet.get_free(), TO_TRANSFER_USDT)

        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.transfer_usdt(2 * TO_TRANSFER_USDT, type='ms', check_status=400)
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.transfer_usdt(TO_TRANSFER_USDT, type='ms')
        self.assert_margin_info(0, 0, 0, 999)

    def test_loan(self):
        self.pass_quiz()

        self.loan('ADA', TO_TRANSFER_USDT / XRP_USDT_PRICE, check_status=400)

        self.transfer_usdt(TO_TRANSFER_USDT)

        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.loan('ADA', TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assert_margin_info(TO_TRANSFER_USDT, TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 2)

        self.loan('ADA', TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))

        self.loan('ADA', TO_TRANSFER_USDT / XRP_USDT_PRICE, check_status=400)

        self.loan('ADA', 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE, type='repay')
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

        self.loan('ADA', 1, type='repay', check_status=400)
        self.assert_margin_info(TO_TRANSFER_USDT, 0, TO_TRANSFER_USDT, 999)

    def print_wallets(self, account=None):
        wallets = Wallet.objects.all()

        if account:
            wallets = wallets.filter(account=account)

        for w in wallets:
            print('%s %s %s: %s' % (w.account, w.asset.symbol, w.market, w.get_free()))

        print()

    @mock.patch('ledger.tasks.margin.warn_risky_level')
    def test_liquidate_no_trade(self, warn_risky_level):
        self.assertEqual(check_margin_level(), 0)

        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        self.assertEqual(check_margin_level(), 0)

        self.loan('ADA', 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE)

        self.assertEqual(check_margin_level(), 0)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))

        set_price(self.xrp, XRP_USDT_PRICE * 2)
        self.assert_margin_info(TO_TRANSFER_USDT, 4 * TO_TRANSFER_USDT, 5 * TO_TRANSFER_USDT, Decimal('1.25'))
        self.assertEqual(check_margin_level(), 0)

        set_price(self.xrp, XRP_USDT_PRICE * 3)
        self.assert_margin_info(TO_TRANSFER_USDT, 6 * TO_TRANSFER_USDT, 7 * TO_TRANSFER_USDT)
        self.assertEqual(check_margin_level(), 1)
        warn_risky_level.assert_called_once()

        set_price(self.xrp, XRP_USDT_PRICE * 5)

        self.assertLess(self.get_margin_info()['margin_level'], Decimal('1.15'))

        self.assertEqual(check_margin_level(), 2)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('1.5'))

    def test_liquidate_trade_same_loan(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)
        self.loan('USDT', 2 * TO_TRANSFER_USDT)

        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.usdt,
            to_asset=self.xrp,
            from_amount=Decimal(3 * TO_TRANSFER_USDT),
            allow_dust=True
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
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())

    def test_liquidate_trade_different_loan(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        loan_amount = 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE
        self.loan(self.xrp.symbol, loan_amount)

        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.xrp,
            to_asset=self.usdt,
            from_amount=Decimal(loan_amount / 2),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)

        self.print_wallets(self.account)

        self.assertEqual(check_margin_level(), 0)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('1.4'))

        set_price(self.xrp, XRP_USDT_PRICE / 2)

        self.assertEqual(check_margin_level(), 0)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))

        set_price(self.xrp, XRP_USDT_PRICE * 1.6)

        self.assertEqual(check_margin_level(), 2)

        self.print_wallets(self.account)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())

    def test_liquidate_trade_with_open_order(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        loan_amount = 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE
        self.loan(self.xrp.symbol, loan_amount)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))
        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.xrp,
            to_asset=self.usdt,
            from_amount=Decimal(loan_amount),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)
        usdt_wallet = self.usdt.get_wallet(self.account, market=Wallet.MARGIN)

        self.assertEqual(usdt_wallet.balance, otc_request.to_amount + TO_TRANSFER_USDT)

        new_order(self.btcusdt, self.account, amount=usdt_wallet.balance / BTC_USDT_PRICE, price=BTC_USDT_PRICE, side=BUY, market=Wallet.MARGIN)

        new_equity = usdt_wallet.balance - 2 * TO_TRANSFER_USDT

        self.assert_margin_info(new_equity, 2 * TO_TRANSFER_USDT, new_equity + 2 * TO_TRANSFER_USDT)

        set_price(self.xrp, XRP_USDT_PRICE * 1.3)

        self.assertEqual(check_margin_level(), 2)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('1.5'))
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())

    def test_liquidate_more_below_one(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        loan_amount = 2 * TO_TRANSFER_USDT / XRP_USDT_PRICE
        self.loan(self.xrp.symbol, loan_amount)

        self.assert_margin_info(TO_TRANSFER_USDT, 2 * TO_TRANSFER_USDT, 3 * TO_TRANSFER_USDT, Decimal('1.5'))
        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.xrp,
            to_asset=self.usdt,
            from_amount=Decimal(loan_amount),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)
        usdt_wallet = self.usdt.get_wallet(self.account, market=Wallet.MARGIN)

        self.assertEqual(usdt_wallet.balance, otc_request.to_amount + TO_TRANSFER_USDT)

        new_order(self.btcusdt, self.account, amount=usdt_wallet.balance / BTC_USDT_PRICE, price=BTC_USDT_PRICE, side=BUY, market=Wallet.MARGIN)

        new_equity = usdt_wallet.balance - 2 * TO_TRANSFER_USDT

        self.assert_margin_info(new_equity, 2 * TO_TRANSFER_USDT, new_equity + 2 * TO_TRANSFER_USDT)

        set_price(self.xrp, XRP_USDT_PRICE * 2)

        self.assertEqual(check_margin_level(), 2)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))

        self.assertTrue(Trx.objects.filter(sender__account=MARGIN_INSURANCE_ACCOUNT).exists())
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())

    def test_close_request(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        loan_amount = 2 * TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.loan(self.btc.symbol, loan_amount)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.btc,
            to_asset=self.usdt,
            from_amount=Decimal(loan_amount),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)

        resp = self.client.post('/api/v1/margin/close/')
        self.assertEqual(resp.status_code, 201)

        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))

    def test_liquidate_more_below_one_transfer_xrp(self):
        self.pass_quiz()
        transfer_amount = TO_TRANSFER_USDT
        self.xrp.get_wallet(self.account).airdrop(transfer_amount)
        self.transfer_xrp(transfer_amount)

        loan_amount = 2 * transfer_amount
        self.loan(self.xrp.symbol, loan_amount)

        self.assert_margin_info(transfer_amount * XRP_USDT_PRICE, 2 * transfer_amount * XRP_USDT_PRICE, 3 * transfer_amount * XRP_USDT_PRICE, Decimal('1.5'))
        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.xrp,
            to_asset=self.usdt,
            from_amount=Decimal(transfer_amount * 3),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)

        set_price(self.xrp, XRP_USDT_PRICE * 3)

        self.assertEqual(check_margin_level(), 2)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))

        self.assertTrue(Trx.objects.filter(sender__account=MARGIN_INSURANCE_ACCOUNT).exists())
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())

    def test_liquidate_more_below_one_borrow_usdt(self):
        self.pass_quiz()
        self.transfer_usdt(TO_TRANSFER_USDT)

        loan_amount = 2 * TO_TRANSFER_USDT
        self.loan(self.usdt.symbol, loan_amount)

        self.assertEqual(check_margin_level(), 0)

        otc_request = OTCRequest.new_trade(
            self.account,
            market=Wallet.MARGIN,
            from_asset=self.usdt,
            to_asset=self.xrp,
            from_amount=Decimal(TO_TRANSFER_USDT * 3),
            allow_dust=True
        )

        OTCTrade.execute_trade(otc_request)

        set_price(self.xrp, XRP_USDT_PRICE / 2)

        self.assertEqual(check_margin_level(), 2)
        self.assertGreaterEqual(self.get_margin_info()['margin_level'], Decimal('2'))

        self.assertTrue(Trx.objects.filter(sender__account=MARGIN_INSURANCE_ACCOUNT).exists())
        self.assertTrue(Trx.objects.filter(receiver__account=MARGIN_INSURANCE_ACCOUNT).exists())
