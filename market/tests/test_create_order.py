from django.test import TestCase, Client

from accounts.models import Account
from ledger.utils.test import new_account
from ledger.models import Asset, Trx
from uuid import uuid4
from market.models import PairSymbol,FillOrder
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

    # def test_fill_order(self):
    #     order = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
    #     order_2 = new_order(self.btcirt, Account.system(), 2, 20000, 'buy')
    #     order.refresh_from_db()
    #
    #     fill_order = FillOrder.objects.last()
    #
    #     self.assertEqual(order.status, 'filled')
    #     self.assertEqual(fill_order.price, 200000)
    #     self.assertEqual(fill_order.amount, 2)

    def test_fill_order_with_different_price(self):
        order_3 = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_4 = new_order(self.btcirt, Account.system(), 2, 200010, 'buy')
        order_3.refresh_from_db()

        fill_order = FillOrder.objects.last()

        self.assertEqual(order_4.status, 'filled')
        self.assertEqual(fill_order.price, 200000)
        self.assertEqual(fill_order.amount, 2)

    def test_not_fill_order(self):
        order_3 = new_order(self.btcirt, Account.system(), 2, 200000, 'sell')
        order_4 = new_order(self.btcirt, Account.system(), 2, 150000, 'buy')

        self.assertEqual(order_4.status, 'new')

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
