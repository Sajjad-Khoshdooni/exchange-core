from decimal import Decimal
from unittest import mock

from django.test import TestCase

from accounts.models import Account
from accounts.utils.test import create_referral, set_referred_by
from ledger.models import Trx, Asset
from ledger.utils.test import new_account
from market.models import PairSymbol, Order, ReferralTrx, Trade
from market.utils.order_utils import new_order


class ReferralTestCase(TestCase):
    def init_accounts(self):
        account_1 = new_account()
        account_1_referral = create_referral(account_1)
        account_2 = new_account()
        account_3 = new_account()
        set_referred_by(account_3, account_1_referral)
        account_3.save()
        self.btc.get_wallet(account_2).airdrop(1000 * 1000 * 1000)
        self.irt.get_wallet(account_3).airdrop(1000 * 1000 * 1000)
        self.usdt.get_wallet(account_3).airdrop(1000 * 1000 * 1000)
        return account_1, account_2, account_3, account_1_referral

    def setUp(self):
        PairSymbol.objects.filter(name='BTCIRT').update(enable=True)
        PairSymbol.objects.filter(name='BTCUSDT').update(enable=True)

        self.irt = Asset.get(Asset.IRT)
        self.btc = Asset.get('BTC')
        self.usdt = Asset.get('USDT')
        self.btcitr = PairSymbol.objects.get(name='BTCIRT')
        self.btcusdt = PairSymbol.objects.get(name='BTCUSDT')
        self.usdtirt = PairSymbol.objects.get(name='USDTIRT')

    def test_referral_btc_irt(self):
        account_1, account_2, account_3, account_1_referral = self.init_accounts()
        order_1 = new_order(self.btcitr, account_2, 2, 200000, Order.SELL)
        order_2 = new_order(self.btcitr, account_3, 2, 200005, Order.BUY)

        order_1.refresh_from_db(), order_2.refresh_from_db()

        trade = Trade.objects.get(order_id=order_1.id)

        trx_referral = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.btc.get_wallet(account_3),
            receiver=self.btc.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            account_1_referral.owner_share_percent / Decimal('100') *
            self.btcitr.taker_fee * trade.amount * trade.price
        )
        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.btcitr.taker_fee * trade.amount
        )

    @mock.patch('market.models.order.get_tether_irt_price')
    @mock.patch('market.models.trade.get_tether_irt_price')
    def test_referral_btc_usdt(self, get_tether_irt_price, get_tether_irt_price_2):
        account_1, account_2, account_3, account_1_referral = self.init_accounts()
        get_tether_irt_price.return_value = 1
        get_tether_irt_price_2.return_value = 1
        print(get_tether_irt_price())

        order_3 = new_order(self.btcusdt, account_2, 2, 200000, Order.SELL)
        order_4 = new_order(self.btcusdt, account_3, 2, 200000, Order.BUY)

        order_3.refresh_from_db(), order_4.refresh_from_db()

        trade = Trade.objects.get(order_id=order_3.id)

        trx_referral = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(account_1),
            scope=Trx.COMMISSION
        )

        fee_trx_referred = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.btc.get_wallet(account_3),
            receiver=self.btc.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            account_1_referral.owner_share_percent / Decimal('100') *
            self.btcitr.taker_fee * trade.amount * trade.price
        )
        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.btcitr.taker_fee * trade.amount
        )

    def test_referral_usdt_irt(self):
        account_1, _, account_3, account_1_referral = self.init_accounts()
        account_3.print()

        order_5 = new_order(self.usdtirt, Account.system(), 20, 20000, Order.BUY)
        order_6 = new_order(self.usdtirt, account_3, 20, 20000, Order.SELL)

        order_7 = new_order(self.usdtirt, Account.system(), 10, 20000, Order.SELL)
        order_8 = new_order(self.usdtirt, account_3, 10, 20000, Order.BUY)

        order_5.refresh_from_db(), order_6.refresh_from_db(), order_7.refresh_from_db(), order_8.refresh_from_db()

        trade = Trade.objects.get(order_id=order_5.id)
        trade_2 = Trade.objects.get(order_id=order_7.id)

        trx_referral = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred = Trx.objects.get(
            group_id=trade.group_id,
            sender=self.irt.get_wallet(account_3),
            receiver=self.irt.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )

        trx_referral_2 = Trx.objects.get(
            group_id=trade_2.group_id,
            sender=self.irt.get_wallet(Account.system()),
            receiver=self.irt.get_wallet(account_1),
            scope=Trx.COMMISSION
        )
        fee_trx_referred_2 = Trx.objects.get(
            group_id=trade_2.group_id,
            sender=self.usdt.get_wallet(account_3),
            receiver=self.usdt.get_wallet(Account.system()),
            scope=Trx.COMMISSION
        )
        self.assertEqual(
            trx_referral.amount,
            account_1_referral.owner_share_percent / Decimal('100') *
            self.usdtirt.taker_fee * trade.amount * trade.price
        )

        self.assertEqual(
            fee_trx_referred.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.usdtirt.taker_fee * trade.amount * trade.price
        )

        self.assertEqual(
            trx_referral_2.amount,
            account_1_referral.owner_share_percent / Decimal('100') *
            self.usdtirt.taker_fee * trade_2.amount * trade_2.price
        )

        self.assertEqual(
            fee_trx_referred_2.amount,
            (1 - ((ReferralTrx.REFERRAL_MAX_RETURN_PERCENT - account_1_referral.owner_share_percent) / Decimal(
                '100'))) *
            self.usdtirt.taker_fee * trade_2.amount
        )
