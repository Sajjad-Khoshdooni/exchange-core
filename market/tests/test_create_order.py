from decimal import Decimal
from uuid import uuid4

from django.test import TestCase, Client
from django.utils import timezone

from accounts.models import Account
from ledger.models import Asset, Trx, Wallet
from ledger.utils.test import new_account
from market.models import PairSymbol, FillOrder, Order
from market.utils import new_order, cancel_order


# todo: check referral for USDTIRT

class CreateOrderTestCase(TestCase):
    def setUp(self):
        PairSymbol.objects.filter(name='BTCIRT').update(enable=True)
        PairSymbol.objects.filter(name='BTCUSDT').update(enable=True)

        self.account = new_account()

        self.account_2 = new_account()
        self.client = Client()

        self.irt = Asset.get(Asset.IRT)
        self.usdt = Asset.get(Asset.USDT)
        self.btc = Asset.get('BTC')

        self.btcirt = PairSymbol.objects.get(name='BTCIRT')
        self.btcusdt = PairSymbol.objects.get(name='BTCUSDT')

        self.fill = FillOrder.objects.all()

        for market in (Wallet.SPOT, Wallet.MARGIN):
            Trx.transaction(
                group_id=uuid4(),
                sender=self.usdt.get_wallet(Account.system()),
                receiver=self.usdt.get_wallet(self.account, market=market),
                amount=1000 * 1000 * 10000,
                scope=Trx.TRANSFER
            )
            Trx.transaction(
                group_id=uuid4(),
                sender=self.irt.get_wallet(Account.system()),
                receiver=self.irt.get_wallet(self.account, market=market),
                amount=1000 * 1000 * 10000,
                scope=Trx.TRANSFER
            )
            Trx.transaction(
                group_id=uuid4(),
                sender=self.btc.get_wallet(Account.system()),
                receiver=self.btc.get_wallet(self.account, market=market),
                amount=1000 * 1000 * 10000,
                scope=Trx.TRANSFER
            )

        self.account.user.margin_quiz_pass_date = timezone.now()
        self.account.user.show_margin = True
        self.account.user.save()

        self.account_2.user.margin_quiz_pass_date = timezone.now()
        self.account_2.user.show_margin = True
        self.account_2.user.save()

    def test_create_order(self):

        self.client.force_login(self.account.user)
        # wallets = self.irt.get_wallet(self.account)
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': 'BTCIRT',
            'amount': '1.5',
            'price': '200000',
            'side': 'buy',
            'fill_type': 'limit',
        })
        self.assertEqual(resp.status_code, 201)

    def test_fill_order(self):
        order = new_order(self.btcirt, Account.system(), 2, 200000, Order.SELL)
        order_2 = new_order(self.btcirt, Account.system(), 2, 200000, Order.BUY)
        order.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order.status, Order.FILLED)
        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 2)

    def test_fill_order_with_different_price(self):
        order_3 = new_order(self.btcirt, Account.system(), 2, 200000, Order.SELL)
        order_4 = new_order(self.btcirt, self.account, 2, 200010, Order.BUY)
        order_3.refresh_from_db(), order_4.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_3)

        trx_asset = Trx.objects.get(
            group_id=fill_order.group_id,
            scope=Trx.TRADE,
            sender=self.btc.get_wallet(Account.system())
        )
        trx_base_asset = Trx.objects.get(
            group_id=fill_order.group_id,
            scope=Trx.TRADE,
            sender=self.irt.get_wallet(self.account)
        )
        trx_taker_fee = Trx.objects.get(
            group_id=fill_order.group_id,
            scope=Trx.COMMISSION,
            sender=self.btc.get_wallet(self.account)
        )
        if fill_order.symbol.maker_fee != 0:
            trx_maker_fee = Trx.objects.get(
                group_id=fill_order.group_id,
                scope=Trx.COMMISSION,
                sender=self.btc.get_wallet(Account.system())
            )
            self.assertEqual(trx_maker_fee, 2 * self.btcirt.maker_fee)

        self.assertEqual(trx_asset.amount, 2)
        self.assertEqual(trx_base_asset.amount, 400000)
        self.assertEqual(trx_taker_fee.amount, 2 * self.btcirt.taker_fee)

        self.assertEqual(order_3.status, Order.FILLED)
        self.assertEqual(order_4.status, Order.FILLED)

        self.assertEqual(order_3.filled_amount, 2)
        self.assertEqual(order_4.filled_amount, 2)

        self.assertEqual(order_3.filled_price, 200000)
        self.assertEqual(order_4.filled_price, 200000)

        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 2)

    def test_fill_three_order(self):
        order_5 = new_order(self.btcirt, Account.system(), 2, 200000, Order.SELL)
        order_6 = new_order(self.btcirt, Account.system(), 3, 200010, Order.SELL)
        order_7 = new_order(self.btcirt, Account.system(), 6, 200020, Order.BUY)

        order_5.refresh_from_db(), order_6.refresh_from_db(), order_7.refresh_from_db()

        fill_order_between_5_7 = FillOrder.objects.get(maker_order=order_5)
        fill_order_between_6_7 = FillOrder.objects.get(maker_order=order_6)

        self.assertEqual(fill_order_between_5_7.taker_fee_amount, 2 * self.btcirt.taker_fee)
        self.assertEqual(fill_order_between_5_7.maker_fee_amount, 2 * self.btcirt.maker_fee)
        self.assertEqual(fill_order_between_6_7.taker_fee_amount, 3 * self.btcirt.taker_fee)
        self.assertEqual(fill_order_between_6_7.maker_fee_amount, 3 * self.btcirt.maker_fee)

        self.assertEqual(order_5.filled_amount, 2)
        self.assertEqual(order_6.filled_amount, 3)
        self.assertEqual(order_7.filled_amount, 5)

        self.assertEqual(order_5.filled_price, 200000)
        self.assertEqual(order_6.filled_price, 200010)

        self.assertEqual(order_5.status, Order.FILLED)
        self.assertEqual(order_6.status, Order.FILLED)
        self.assertEqual(order_7.status, Order.NEW)

        self.assertEqual(fill_order_between_5_7.amount, 2)
        self.assertEqual(fill_order_between_6_7.amount, 3)

        self.assertEqual(fill_order_between_5_7.price, 200000)
        self.assertEqual(fill_order_between_6_7.price, 200010)

    def test_not_fill_order(self):
        order_8 = new_order(self.btcirt, Account.system(), 2, 200000, Order.SELL)
        order_9 = new_order(self.btcirt, Account.system(), 2, 150000, Order.BUY)

        order_8.refresh_from_db(), order_9.refresh_from_db()

        self.assertEqual(order_8.filled_amount, 0)
        self.assertEqual(order_9.filled_amount, 0)
        self.assertEqual(order_8.status, Order.NEW)
        self.assertEqual(order_9.status, Order.NEW)

    def test_cancel_order_after_partial_filled(self):

        order_10 = new_order(self.btcirt, Account.system(), 20, 200000, Order.SELL)
        order_11 = new_order(self.btcirt, Account.system(), 10, 200005, Order.BUY)

        cancel_order(order_10)

        order_10.refresh_from_db(), order_11.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_10)

        self.assertEqual(order_10.status, Order.CANCELED)
        self.assertEqual(order_11.status, Order.FILLED)

        self.assertEqual(order_10.filled_amount, 10)
        self.assertEqual(order_11.filled_amount, 10)

        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 10)

    def test_cancel_order_after_complete_filled(self):

        order_12 = new_order(self.btcirt, Account.system(), 20, 200000, Order.SELL)
        order_13 = new_order(self.btcirt, Account.system(), 20, 200005, Order.BUY)

        cancel_order(order_12)

        order_12.refresh_from_db(), order_13.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_12)

        self.assertEqual(order_12.status, Order.FILLED)
        self.assertEqual(order_13.status, Order.FILLED)

        self.assertEqual(order_12.filled_amount, 20)
        self.assertEqual(order_13.filled_amount, 20)

        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 20)

    def test_cancel_before_fill(self):

        order_14 = new_order(self.btcirt, Account.system(), 20, 200000, Order.SELL)
        cancel_order(order_14)
        order_15 = new_order(self.btcirt, Account.system(), 20, 200000, Order.BUY)

        order_14.refresh_from_db(), order_15.refresh_from_db()

        self.assertEqual(order_14.status, Order.CANCELED)
        self.assertEqual(order_15.status, Order.NEW)

        self.assertEqual(order_14.filled_amount, 0)
        self.assertEqual(order_15.filled_amount, 0)

    def test_not_enough_for_sell(self):
        self.client.force_login(self.account_2.user)
        # wallet = self.btc.get_wallet(self.account_2)
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': 'BTCIRT',
            'amount': '10',
            'price': '300000',
            'side': 'sell',
            'fill_type': 'limit',
        })
        self.assertEqual(resp.status_code, 400)

    def test_market_sell_order(self):
        limit_order = new_order(self.btcirt, Account.system(), 2, 2000000, Order.BUY)
        order = new_order(self.btcirt, Account.system(), Decimal('0.1'), None, Order.SELL, fill_type=Order.MARKET)
        order.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order.status, Order.FILLED)
        self.assertEqual(fill_order.price, 2000000)
        self.assertEqual(fill_order.amount, Decimal('0.1'))

    def test_market_sell_order(self):
        limit_order = new_order(self.btcirt, Account.system(), 2, 2000000, Order.SELL)
        order = new_order(self.btcirt, Account.system(), Decimal('0.1'), None, Order.BUY, fill_type=Order.MARKET)
        order.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order.status, Order.FILLED)
        self.assertEqual(fill_order.price, 2000000)
        self.assertEqual(fill_order.amount, Decimal('0.1'))

    def test_market_order_large_amount(self):
        new_order(self.btcirt, Account.system(), 1, 2000000, Order.BUY)
        order = new_order(self.btcirt, Account.system(), 2, None, Order.SELL, fill_type=Order.MARKET)
        order.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order.status, Order.CANCELED)
        self.assertEqual(fill_order.price, 2000000)
        self.assertEqual(fill_order.amount, 1)

    def test_market_order_multi_match_price(self):
        new_order(self.btcirt, Account.system(), Decimal('0.5'), 2000000, Order.BUY)
        new_order(self.btcirt, Account.system(), Decimal('0.5'), 1980000, Order.BUY)
        order = new_order(self.btcirt, Account.system(), 2, None, Order.SELL, fill_type=Order.MARKET)
        order.refresh_from_db()

        self.assertEqual(order.status, Order.CANCELED)

        fill_orders = FillOrder.objects.all().order_by('-id')[:2]
        for fill_order in fill_orders:
            self.assertEqual(fill_order.price, fill_order.maker_order.price)
            self.assertEqual(fill_order.amount, Decimal('0.5'))

    def test_market_order_multi_match_price_unmatched_orders(self):
        new_order(self.btcirt, Account.system(), Decimal('0.5'), 2000000, Order.BUY)
        new_order(self.btcirt, Account.system(), Decimal('0.5'), 1980000, Order.BUY)
        new_order(self.btcirt, Account.system(), Decimal('0.5'), 1900000, Order.BUY)
        order = new_order(self.btcirt, Account.system(), 2, None, Order.SELL, fill_type=Order.MARKET)
        order.refresh_from_db()

        self.assertEqual(order.status, Order.CANCELED)
        self.assertEqual(order.filled_amount, 1)

        fill_orders = FillOrder.objects.all().order_by('-id')[:2]
        for fill_order in fill_orders:
            self.assertEqual(fill_order.price, fill_order.maker_order.price)
            self.assertEqual(fill_order.amount, Decimal('0.5'))

    def test_margin_create_order(self):
        self.client.force_login(self.account.user)
        # wallets = self.irt.get_wallet(self.account)
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': 'BTCUSDT',
            'amount': '1.5',
            'price': '200000',
            'side': 'buy',
            'fill_type': 'limit',
            'market': 'margin'
        })
        self.assertEqual(resp.status_code, 201)

    def test_margin_match_order(self):
        self.client.force_login(self.account.user)
        # wallets = self.irt.get_wallet(self.account)
        order = new_order(self.btcusdt, Account.system(), 2, 20000, Order.SELL)
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': 'BTCUSDT',
            'amount': '1.5',
            'price': '20000',
            'side': 'buy',
            'fill_type': 'limit',
            'market': 'margin'
        })

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Decimal(resp.json()['amount']), Decimal('1.5'))

        fill_order = FillOrder.objects.last()
        order.refresh_from_db()
        self.assertEqual(fill_order.price, 20000)
        self.assertEqual(fill_order.amount, Decimal('1.5'))
        self.assertEqual(fill_order.taker_order.wallet.market, Wallet.MARGIN)
        self.assertEqual(fill_order.taker_order.base_wallet.market, Wallet.MARGIN)

    def test_not_enough_for_sell_margin(self):
        self.client.force_login(self.account_2.user)
        # wallet = self.btc.get_wallet(self.account_2)
        resp = self.client.post('/api/v1/market/orders/', {
            'symbol': 'BTCUSDT',
            'amount': '10',
            'price': '300000',
            'side': 'sell',
            'fill_type': 'limit',
            'market': 'margin'
        })
        self.assertEqual(resp.status_code, 400)
