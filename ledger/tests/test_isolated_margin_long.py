from decimal import Decimal

from django.db.models import Q
from django.test import Client
from django.test import TestCase
from django.utils import timezone

from ledger.models import Asset, Wallet, MarginPosition, MarginLeverage
from ledger.utils.external_price import SELL, BUY, LONG
from ledger.utils.precision import floor_precision
from ledger.utils.test import new_account, set_price
from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import PairSymbol
from market.utils.order_utils import new_order

USDT_IRT_PRICE = 20000
BTC_USDT_PRICE = Decimal('1000')

TO_TRANSFER_USDT = 100


class LongIsolatedMarginTestCase(TestCase):

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

        # self.btc.get_wallet(self.account).airdrop(TO_TRANSFER_USDT / BTC_USDT_PRICE * 3)
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
                'leverage': Decimal('2')
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

    def print_wallets(self, account=None):
        wallets = Wallet.objects.all()

        print('///////////////////////WALLETS///////////////////////')
        if account:
            wallets = wallets.filter(account=account)

        for w in wallets:
            print('%s %s %s %s %s: %s' % (w.id, w.account, w.asset.symbol, w.market, w.variant, w.get_free()))

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
            Q(balance__lt=Decimal(0)) | Q(balance__gt=Decimal('0.000001')),
            account=account,
            market=Wallet.MARGIN,
            variant__isnull=False,
        ).count()

        self.assertEqual(negetive_wallets, Decimal('0'))
        self.assertEqual(mp.status, MarginPosition.CLOSED)

    def test_long_buy(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT/2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            balance = self.usdt.get_wallet(self.account2).balance / BTC_USDT_PRICE
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=balance, market=Wallet.SPOT, price=BTC_USDT_PRICE)
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=balance, market=Wallet.SPOT, price=BTC_USDT_PRICE - 1)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.assertEqual(mp.debt_amount, loan_amount * BTC_USDT_PRICE/2)
        print('position', mp.debt_amount, mp.liquidation_price, mp.equity)
        self.assertTrue(mp.liquidation_price == Decimal('550'))
        self.assertEqual(mp.side, LONG)

        with WalletPipeline() as pipeline:
            mp.liquidate(pipeline, False)

        self.assert_liquidation(self.account, self.btcusdt)

    def test_long_buy_market(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            balance = self.usdt.get_wallet(self.account2).balance / BTC_USDT_PRICE
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=balance, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True, fill_type='market')

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.assertEqual(mp.debt_amount, loan_amount * BTC_USDT_PRICE/2)
        print('position', mp.debt_amount, mp.liquidation_price, mp.equity)
        self.assertTrue(mp.liquidation_price >= Decimal('550'))
        self.assertEqual(mp.side, LONG)

    def test_long_buy2(self):
        self.transfer_usdt_api(2 * TO_TRANSFER_USDT)
        trade_amount = floor_precision(TO_TRANSFER_USDT / BTC_USDT_PRICE / 6, 2)
        self.print_wallets(self.account)

        liquidation_price = Decimal('550')
        self.place_order(amount=trade_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('margin', mp.liquidation_price, mp.debt_amount, mp.total_balance)
        self.print_wallets(self.account)
        self.assertTrue(mp.liquidation_price == liquidation_price)
        self.assertEqual(mp.side, LONG)
        liquidation_price = mp.liquidation_price

        self.place_order(amount=trade_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()

        print('margin', mp.liquidation_price, mp.debt_amount, mp.total_balance)
        self.print_wallets(self.account)

        self.place_order(amount=trade_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()

        print('margin', mp.liquidation_price, mp.debt_amount, mp.total_balance)
        self.print_wallets(self.account)
        liquidation_price = mp.liquidation_price

        print('///////////////////////////////////////////')

        self.place_order(amount=trade_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=trade_amount, fill_type='market')
        mp.refresh_from_db()
        print('margin', mp.liquidation_price, mp.debt_amount, mp.total_balance)

    def test_long_buy3(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT/2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.assertEqual(mp.debt_amount, loan_amount * BTC_USDT_PRICE/2)
        print('position', mp.debt_amount, mp.liquidation_price, mp.equity)
        self.assertTrue(mp.liquidation_price == Decimal('550'))
        self.assertEqual(mp.side, LONG)

        self.place_order(amount=floor_precision(loan_amount/6, 4), side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=False)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount/3, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)
        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print('position', mp.debt_amount, mp.liquidation_price, mp.equity)

    def test_long_buy4(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT/2)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        self.print_wallets(self.account)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.assertEqual(mp.debt_amount, loan_amount * BTC_USDT_PRICE/2)
        print('position', mp.debt_amount, mp.liquidation_price, mp.equity)
        self.assertTrue(mp.liquidation_price == Decimal('550'))
        self.assertEqual(mp.side, LONG)

        self.place_order(amount=loan_amount, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount, market=Wallet.SPOT, price=BTC_USDT_PRICE)

        mp.refresh_from_db()
        print('mp', mp.debt_amount, mp.total_balance, mp.liquidation_price, mp.side, mp.status, mp.equity)
        self.print_wallets(self.account)
        self.assertEqual(mp.status, MarginPosition.CLOSED)

    def test_long_buy_liquidate(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE / 2
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount * 4, market=Wallet.SPOT,
                      price=mp.liquidation_price)
            new_order(pipeline, self.btcusdt, self.account3, side=SELL, amount=loan_amount, market=Wallet.SPOT,
                      price=mp.liquidation_price)

        self.assert_liquidation(self.account, self.btcusdt)

        print('************************************insurance_account_wallet************************************')
        self.print_wallets(self.account)
        mp.refresh_from_db()
        print(f'margin position: {mp.liquidation_price}', mp.equity)

    def test_long_buy_liquidate2(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        self.place_order(amount=loan_amount/10, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE)

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        print(f'margin position: {mp.liquidation_price}', mp.equity)
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount * 4, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price / 2))
            new_order(pipeline, self.btcusdt, self.account3, side=SELL, amount=loan_amount / 2, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price / 2))
        self.print_wallets(self.account)

        self.assert_liquidation(self.account, self.btcusdt)
        mp.refresh_from_db()
        print(f'margin position: {mp.liquidation_price}', mp.equity)

    def test_long_buy_partial_liquidate(self):
        self.transfer_usdt_api(TO_TRANSFER_USDT)
        loan_amount = TO_TRANSFER_USDT / BTC_USDT_PRICE
        self.print_wallets(self.account)
        self.place_order(amount=loan_amount, side=BUY, market=Wallet.MARGIN, price=BTC_USDT_PRICE, is_open_position=True)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=SELL, amount=loan_amount, market=Wallet.SPOT,
                      price=BTC_USDT_PRICE)

        self.place_order(amount=loan_amount/4, side=SELL, market=Wallet.MARGIN, price=BTC_USDT_PRICE)
        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount/4, market=Wallet.SPOT,
                      fill_type='market')

        mp = MarginPosition.objects.filter(account=self.account, symbol=self.btcusdt).first()
        self.print_wallets(self.account)

        with WalletPipeline() as pipeline:
            new_order(pipeline, self.btcusdt, self.account2, side=BUY, amount=loan_amount * 3, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price))
            new_order(pipeline, self.btcusdt, self.account3, side=SELL, amount=loan_amount / 2, market=Wallet.SPOT,
                      price=Decimal(mp.liquidation_price))
        self.print_wallets(self.account)

        self.assert_liquidation(self.account, self.btcusdt)

