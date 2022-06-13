from decimal import Decimal
from unittest import mock
from uuid import uuid4

from django.test import TestCase

from accounts.models import Account
from accounts.utils.test import create_referral, set_referred_by
from ledger.models import Trx, Asset
from ledger.utils.test import new_account
from market.models import PairSymbol, Order, FillOrder, ReferralTrx
from market.utils import new_order


class ReferralTestCase(TestCase):
    def setUp(self):
        PairSymbol.objects.filter(name='BTCIRT').update(enable=True)
        PairSymbol.objects.filter(name='BTCUSDT').update(enable=True)
        self.account_1 = new_account()
        self.account_1_referral = create_referral(self.account_1)
        self.account_2 = new_account()
        self.account_3 = new_account()

        set_referred_by(self.account_3, self.account_1_referral)
        self.account_3.save()

        self.irt = Asset.get(Asset.IRT)
        self.btc = Asset.get('BTC')
        self.usdt = Asset.get('USDT')
        self.btcitr = PairSymbol.objects.get(name='BTCIRT')
        self.btcusdt = PairSymbol.objects.get(name='BTCUSDT')
        self.usdtirt = PairSymbol.objects.get(name='USDTIRT')

        Trx.transaction(
            group_id=uuid4(),
            sender=self.btc.get_wallet(Account.system()),
            receiver=self.btc.get_wallet(self.account_2),
            amount=1000 * 1000 * 1000,
            scope=Trx.TRANSFER
        )

        Trx.transaction(
            group_id=uuid4(),
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_3),
            amount=1000 * 1000 * 10000,
            scope=Trx.TRANSFER
        )

        Trx.transaction(
            group_id=uuid4(),
            sender=self.usdt.get_wallet(Account.system()),
            receiver=self.usdt.get_wallet(self.account_3),
            amount=1000 * 1000 * 10000,
            scope=Trx.TRANSFER
        )

    def test_referral_btc_irt(self):
        order_1 = new_order(self.btcitr, self.account_2, 2, 200000, Order.SELL)
        order_2 = new_order(self.btcitr, self.account_3, 2, 200005, Order.BUY)

        order_1.refresh_from_db(), order_2.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_1)

        trx_referral = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.btc.get_wallet(self.account_3),
            receiver=self.btc.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') *
            self.btcitr.taker_fee * fill_order.amount * fill_order.price
        )
        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - self.account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.btcitr.taker_fee * fill_order.amount
        )

    @mock.patch('market.models.order.get_tether_irt_price')
    @mock.patch('market.models.fill_order.get_tether_irt_price')
    def test_referral_btc_usdt(self, get_tether_irt_price, get_tether_irt_price_2):
        get_tether_irt_price.return_value = 1
        get_tether_irt_price_2.return_value = 1
        print(get_tether_irt_price())

        order_3 = new_order(self.btcusdt, self.account_2, 2, 200000, Order.SELL)
        order_4 = new_order(self.btcusdt, self.account_3, 2, 200000, Order.BUY)

        order_3.refresh_from_db(), order_4.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_3)

        trx_referral = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_1),
            scope=Trx.COMMISSION
        )

        fee_trx_referred = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.btc.get_wallet(self.account_3),
            receiver=self.btc.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') *
            self.btcitr.taker_fee * fill_order.amount * fill_order.price
        )
        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - self.account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.btcitr.taker_fee * fill_order.amount
        )

    def test_referral_usdt_irt(self):
        self.account_3.print()

        order_5 = new_order(self.usdtirt, Account.system(), 20, 20000, Order.BUY)
        order_6 = new_order(self.usdtirt, self.account_3, 20, 20000, Order.SELL)

        order_7 = new_order(self.usdtirt, Account.system(), 10, 20000, Order.SELL)
        order_8 = new_order(self.usdtirt, self.account_3, 10, 20000, Order.BUY)

        order_5.refresh_from_db(), order_6.refresh_from_db(), order_7.refresh_from_db(), order_8.refresh_from_db()

        fill_order = FillOrder.objects.get(maker_order=order_5)
        fill_order_2 = FillOrder.objects.get(maker_order=order_7)

        trx_referral = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(self.account_3),
            receiver=self.irt.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )

        trx_referral_2 = Trx.objects.get(
            group_id=fill_order_2.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred_2 = Trx.objects.get(
            group_id=fill_order_2.group_id,
            sender=self.usdt.get_wallet(self.account_3),
            receiver=self.usdt.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') *
            self.usdtirt.taker_fee * fill_order.amount * fill_order.price
        )

        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - self.account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.usdtirt.taker_fee * fill_order.amount * fill_order.price
        )

        self.assertEqual(
            trx_referral_2.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') *
            self.usdtirt.taker_fee * fill_order_2.amount * fill_order_2.price
        )

        self.assertEqual(
            fee_trx_referred_2.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - self.account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.usdtirt.taker_fee * fill_order_2.amount
        )
