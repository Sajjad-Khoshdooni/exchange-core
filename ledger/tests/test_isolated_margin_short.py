from decimal import Decimal

from django.db.models import Sum
from django.test import Client
from django.test import TestCase
from django.utils import timezone

from accounting.models import Account
from ledger.margin.closer import MARGIN_INSURANCE_ACCOUNT
from ledger.models import Asset, Wallet, MarginPosition, MarginLeverage
from ledger.utils.external_price import SELL, BUY, SHORT
from ledger.utils.precision import floor_precision
from ledger.utils.test import new_account, set_price
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol
from market.utils.order_utils import new_order

USDT_IRT_PRICE = 20000
BTC_USDT_PRICE = Decimal('1000')

TO_TRANSFER_USDT = 100


class ShortIsolatedMarginTestCase(TestCase):

    def setUp(self) -> None:
        self.insurance_account = new_account()

        self.account = new_account()
        self.user = self.account.user
        self.user.show_margin = True
        self.user.margin_quiz_pass_date = timezone.now()
        self.user.save()

        self.account2 = new_account()
        self.user2 = self.account2.user
        self.user2.show_margin = True
        self.user2.margin_quiz_pass_date = timezone.now()
        self.user2.save()

        self.account3 = new_account()
        self.user3 = self.account3.user
        self.user3.show_margin = True
        self.user3.margin_quiz_pass_date = timezone.now()
        self.user3.save()

        self.usdt = Asset.get(Asset.USDT)

        self.btc = Asset.get('BTC')

        self.usdt.get_wallet(self.account).airdrop(TO_TRANSFER_USDT * 3)

        self.usdt.get_wallet(self.account2).airdrop(TO_TRANSFER_USDT * 30)
        self.btc.get_wallet(self.account2).airdrop(TO_TRANSFER_USDT * 30)

        self.usdt.get_wallet(self.account3).airdrop(TO_TRANSFER_USDT * 30)
        self.btc.get_wallet(self.account3).airdrop(TO_TRANSFER_USDT * 30)

        self.client = Client()
        self.client.force_login(self.user)

        set_price(self.usdt, USDT_IRT_PRICE)
        set_price(self.btc, int(BTC_USDT_PRICE))

        self.btcusdt = PairSymbol.objects.get(name='BTCUSDT')
        self.btcusdt.enable = True
        self.btcusdt.margin_enable = True
        self.btcusdt.last_trade_price = BTC_USDT_PRICE
        self.btcusdt.save()

        self.btc.enable = True
        self.btc.save()
        self.usdt.enable = True
        self.usdt.save()
        MarginLeverage.objects.update_or_create(
            account=self.account,
            defaults={
                'leverage': Decimal('1')
            }
        )

    def transfer_usdt_api(self, amount, type: str = 'sm', check_status=201):
        resp = self.client.post('/api/v1/margin/transfer/', {
            'amount': amount,
            'type': type,
            'coin': 'USDT',
            'symbol': 'BTCUSDT'
        })
        print(resp.json())
        self.assertEqual(resp.status_code, check_status)
        self.get_max()

    def get_position_api(self, check_status=200):
        resp = self.client.get('/api/v2/margin/positions/', {
            'symbol': 'BTCUSDT'
        })
        print(resp.json())
        self.assertEqual(resp.status_code, check_status)

    def transfer_btc_api(self, amount, type: str = 'sm', check_status=201):
        resp = self.client.post('/api/v1/margin/transfer/', {
            'amount': amount,
            'type': type,
            'coin': 'BTC',
            'symbol': 'BTCUSDT'
        })
        self.assertEqual(resp.status_code, check_status)

    def print_wallets(self, account=None):
        wallets = Wallet.objects.all()

        print('///////////////////////WALLETS///////////////////////')
        if account:
            wallets = wallets.filter(account=account)

        for w in wallets:
            print('%s %s %s %s: %s' % (w.account, w.asset.symbol, w.market, w.variant, w.get_free()))

        print("/////////////////////////////////////////////////////")

    def place_order(self, amount, price, side, symbol='BTCUSDT', market='spot', fill_type='limit', is_open_position=False, check_status=201):
        print('place order')
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': symbol,
            'side': side,
            'price': price,
            'amount': amount,
            'fill_type': fill_type,
            'market': market,
            'is_open_position': is_open_position
        })
        print(resp.json())
        self.assertEqual(resp.status_code, check_status)

    def assert_liquidation(self, account, symbol):
        mp = MarginPosition.objects.filter(account=account, symbol=symbol).first()

        negetive_wallets = Wallet.objects.filter(
            account=account,
            market=Wallet.MARGIN,
            variant__isnull=False,
            balance__lt=Decimal(0)
        ).count()

        self.assertEqual(negetive_wallets, Decimal('0'))
        self.assertEqual(mp.status, MarginPosition.CLOSED)

    def get_max(self):
        free = self.btcusdt.base_asset.get_wallet(
            self.account, Wallet.MARGIN, None
        ).balance
        a = {
            'max_buy_volume': abs(Wallet.get_margin_position_max_asset_by_wallet(Decimal('0'), free,
                                                                                 price=BTC_USDT_PRICE,
                                                                                 side='buy')),
            'max_sell_volume': abs(Wallet.get_margin_position_max_asset_by_wallet(Decimal('0'), free,
                                                                                  price=BTC_USDT_PRICE,
                                                                                  side='sell')),
        }
        print(a)
        return a

    def test_short_sell(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT / 2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE / 2
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            balance = self.usdt.get_wallet(self.account2).balance / BTC_USDT_PRICE
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=balance, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)
        self.assertEqual(mp.debt_amount, loan_amount)
        self.assertEqual(mp.side, SHORT)
        self.assertTrue(mp.liquidation_price > Decimal('1818'))

    def test_short_sell2(self):
        self.transfer_usdt_api(2 * TO_TRANSFER_USDT)
        trade_amount = floor_precision(TO_TRANSFER_USDT / BTC_USDT_PRICE / 6, 2)
        self.print_wallets(self.account)

        liquidation_price = Decimal('0')
        self.place_order(amount=trade_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=trade_amount, fill_type='market')

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)
        self.print_wallets(self.account)
        self.assertTrue(mp.liquidation_price > liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        # self.transfer_usdt_api(floor_precision(Decimal(TO_TRANSFER_USDT/3), 2), 'mp')

        self.place_order(amount=trade_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.print_wallets(self.account)
        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print(mp.liquidation_price, liquidation_price, mp.debt_amount, mp.total_balance)
        self.print_wallets(self.account)
        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount/2, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount/2, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE + 1)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, SHORT)

    def test_short_sell3(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT / 2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE / 2
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)
        self.assertEqual(mp.debt_amount, loan_amount)
        self.assertEqual(mp.side, SHORT)
        self.assertTrue(mp.liquidation_price > Decimal('1818'))

        self.place_order(amount=floor_precision(loan_amount/6, 4), side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

    def test_short_sell4(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT / 2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE / 2
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side, mp.status)
        self.assertEqual(mp.debt_amount, loan_amount)
        self.assertEqual(mp.side, SHORT)
        self.assertTrue(mp.liquidation_price > Decimal('1818'))

        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        mp.refresh_from_db()
        self.assertEqual(mp.status, MarginPosition.CLOSED)
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side, mp.status)
        self.print_wallets(self.account)

    def test_short_sell_liquidate(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE / 2
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount * 2, market=Wallet.SPOT,
                      price=mp.liquidation_price)
            new_order(pipeline, self.btcusdt, self.account3, side=BUY, amount=loan_amount/2, market=Wallet.SPOT,
                      price=mp.liquidation_price)

        self.print_wallets(self.account)
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side, mp.status)

        self.assert_liquidation(self.account, self.btcusdt)

    def test_short_sell_liquidate2(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=False)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount * 3, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price * 10))
            new_order(pipeline, self.btcusdt, self.account3, side=BUY, amount=loan_amount/2, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price * 10))
        self.print_wallets(self.account)

        self.assert_liquidation(self.account, self.btcusdt)

    def test_short_sell_partial_liquidate(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.place_order(amount=loan_amount/2, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE / 2)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount/2, market=Wallet.SPOT,
                      fill_type='market')

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount * 3, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price))
            new_order(pipeline, self.btcusdt, self.account3, side=BUY, amount=loan_amount/2, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price))
        self.print_wallets(self.account)
        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side)

        self.assert_liquidation(self.account, self.btcusdt)
