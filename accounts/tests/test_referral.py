from uuid import uuid4
from decimal import Decimal
from django.test import TestCase
from unittest import mock

import ledger.utils.price
from accounts.models import Account
from ledger.models import Trx, Asset
from market.models import PairSymbol, Order, FillOrder,ReferralTrx
from ledger.utils.test import new_account
from market.utils import new_order
from accounts.utils.test import create_referral, set_referred_by


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
        trx_referred = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_3),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') * ReferralTrx.REFERRAL_MAX_RETURN_PERCENT *
            self.btcitr.taker_fee * fill_order.amount * fill_order.price
        )
        self.assertEqual(
            trx_referred.amount,
            (Decimal('1') - (self.account_1_referral.owner_share_percent) / Decimal('100')) *
            ReferralTrx.REFERRAL_MAX_RETURN_PERCENT * self.btcitr.taker_fee * fill_order.amount * fill_order.price
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
        trx_referred = Trx.objects.get(
            group_id=fill_order.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(self.account_3),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            self.account_1_referral.owner_share_percent / Decimal('100') * ReferralTrx.REFERRAL_MAX_RETURN_PERCENT *
            self.btcitr.taker_fee * fill_order.amount * fill_order.price
        )
        self.assertEqual(
            trx_referred.amount,
            (Decimal('1') - (self.account_1_referral.owner_share_percent) / Decimal('100')) *
            ReferralTrx.REFERRAL_MAX_RETURN_PERCENT * self.btcitr.taker_fee * fill_order.amount * fill_order.price
        )
