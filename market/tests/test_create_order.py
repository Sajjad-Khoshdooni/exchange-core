from django.test import TestCase, Client
from ledger.utils.precision import get_presentation_amount
from accounts.models import Account
from ledger.utils.test import new_account
from ledger.models import Asset, Trx
from uuid import uuid4
from market.models import PairSymbol, FillOrder, Order
from market.utils import new_order, cancel_order


class CreateOrderTestCase(TestCase):
    def setUp(self):
        PairSymbol.objects.filter(name='BTCIRT').update(enable=True)

        self.account = new_account()
        self.account_2 = new_account()
        self.client = Client()

        self.irt = Asset.get(Asset.IRT)
        self.btc = Asset.get('BTC')

        self.btcirt = PairSymbol.objects.get(name='BTCIRT')

        self .fill = FillOrder.objects.all()

        Trx.transaction(
            group_id=uuid4(),
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account),
            amount=1000 * 1000 * 10000,
            scope=Trx.TRANSFER
        )
        Trx.transaction(
            group_id=uuid4(),
            sender=self.btc.get_wallet(Account.system()),
            receiver=self.btc.get_wallet(self.account),
            amount=1000 * 1000 * 10000,
            scope=Trx.TRANSFER
        )

    def test_create_order(self):

        self.client.force_login(self.account.user)
        wallets = self.irt.get_wallet(self.account)
        resp = self.client.post('/api/v1/market/orders/', {
            'wallet': wallets.id,
            'symbol': 'BTCIRT',
            'amount': '1.5',
            'price': '200000',
            'side': 'buy',
            'fill_type': 'limit',
        })
        self.assertEqual(resp.status_code, 201)

    def test_fill_order(self):
        order = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_2 = new_order(self.btcirt, Account.system(), 2, 200000, 'buy')
        order.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order.status, 'filled')
        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 2)

    def test_fill_order_with_different_price(self):
        order_3 = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_4 = new_order(self.btcirt, self.account, 2, 200010, 'buy')
        order_3.refresh_from_db()

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
        wallet = self.btc.get_wallet(self.account_2)
        resp = self.client.post('/api/v1/market/orders/', {
            'wallet': wallet.id,
            'symbol': 'BTCIRT',
            'amount': '10',
            'price': '300000',
            'side': 'sell',
            'fill_type': 'limit',
        })
        self.assertEqual(resp.status_code, 400)
