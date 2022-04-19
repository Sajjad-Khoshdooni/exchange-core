from django.test import TestCase, Client
from ledger.utils.precision import get_presentation_amount
from accounts.models import Account
from ledger.utils.test import new_account
from ledger.models import Asset, Trx
from uuid import uuid4
from market.models import PairSymbol, FillOrder
from market.utils import new_order


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
        order_4 = new_order(self.btcirt, Account.system(), 2, 200010, 'buy')
        order_3.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order_3.status, 'filled')
        self.assertEqual(order_4.status, 'filled')

        self.assertEqual(order_3.filled_amount, 2)
        self.assertEqual(order_4.filled_amount, 2)

        self.assertEqual(order_3.filled_price, 200000)
        self.assertEqual(order_4.filled_price, 200000)

        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 2)

    def test_fill_three_order(self):
        order_5 = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_6 = new_order(self.btcirt, Account.system(), 3, 200010, 'sell')
        order_7 = new_order(self.btcirt, Account.system(), 6, 200020, 'buy')

        order_5.refresh_from_db(), order_6.refresh_from_db(), order_7.refresh_from_db()

        fill_order_between_5_7 = FillOrder.objects.get(maker_order=order_5)
        fill_order_between_6_7 = FillOrder.objects.get(maker_order=order_6)

        # todo use symbol fee amounts
        self.assertEqual(get_presentation_amount(fill_order_between_5_7.taker_fee_amount), 2 * self.btcirt.taker_fee)
        self.assertEqual(fill_order_between_5_7.maker_fee_amount, 2 * self.btcirt.maker_fee)
        self.assertEqual(get_presentation_amount(fill_order_between_6_7.taker_fee_amount), 3 * self.btcirt.taker_fee)
        self.assertEqual(fill_order_between_6_7.maker_fee_amount, 3 * self.btcirt.maker_fee)

        self.assertEqual(order_5.filled_amount, 2)
        self.assertEqual(order_6.filled_amount, 3)
        self.assertEqual(order_7.filled_amount, 5)

        self.assertEqual(order_5.filled_price, 200000)
        self.assertEqual(order_6.filled_price, 200010)

        self.assertEqual(order_5.status, 'filled')
        self.assertEqual(order_6.status, 'filled')
        self.assertEqual(order_7.status, 'new')

        self.assertEqual(fill_order_between_5_7.amount, 2)
        self.assertEqual(fill_order_between_6_7.amount, 3)

        self.assertEqual(fill_order_between_5_7.price, 200000)
        self.assertEqual(fill_order_between_6_7.price, 200010)

    def test_not_fill_order(self):
        order_8 = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_9 = new_order(self.btcirt, Account.system(), 2, 150000, 'buy')

        order_8.refresh_from_db(), order_9.refresh_from_db()

        self.assertEqual(order_8.filled_amount, 0)
        self.assertEqual(order_9.filled_amount, 0)
        self.assertEqual(order_8.status, 'new')
        self.assertEqual(order_9.status, 'new')

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
