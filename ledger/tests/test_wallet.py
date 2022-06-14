from uuid import uuid4

from django.db import IntegrityError
from django.test import TestCase

from accounts.models import Account
from ledger.models import Asset, Trx
from ledger.utils.test import new_account


class WalletTestCase(TestCase):
    def setUp(self):
        self.account = new_account()
        self.usdt = Asset.get(Asset.USDT)
        self.wallet = self.usdt.get_wallet(self.account)
        self.system_wallet = self.usdt.get_wallet(Account.system())

    def test_transaction(self):
        Trx.transaction(
            sender=self.system_wallet,
            receiver=self.wallet,
            amount=1,
            scope=Trx.TRANSFER,
            group_id=uuid4()
        )

        self.assertEqual(self.wallet.balance, 1)
        self.assertEqual(self.wallet.locked, 0)
        self.assertEqual(self.system_wallet.balance, -1)

        Trx.transaction(
            sender=self.wallet,
            receiver=self.system_wallet,
            amount=1,
            scope=Trx.TRANSFER,
            group_id=uuid4()
        )

        self.assertEqual(self.wallet.balance, 0)
        self.assertEqual(self.wallet.locked, 0)
        self.assertEqual(self.system_wallet.balance, 0)

        try:
            Trx.transaction(
                sender=self.wallet,
                receiver=self.system_wallet,
                amount=1,
                scope=Trx.TRANSFER,
                group_id=uuid4()
            )

            self.fail('Should fail here!')
        except IntegrityError:
            pass

    def test_lock(self):
        Trx.transaction(
            sender=self.system_wallet,
            receiver=self.wallet,
            amount=10,
            scope=Trx.TRANSFER,
            group_id=uuid4()
        )

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 0)
        self.assertEqual(self.system_wallet.balance, -10)

        self.wallet.refresh_from_db()
        self.system_wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 0)
        self.assertEqual(self.system_wallet.balance, -10)

        lock = self.wallet.lock_balance(4)

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 4)
        self.assertEqual(self.system_wallet.balance, -10)

        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 4)
        self.assertEqual(self.system_wallet.balance, -10)

        lock.decrease_lock(2)
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 2)
        self.assertEqual(self.system_wallet.balance, -10)

        lock.release()
        self.wallet.refresh_from_db()

        self.assertEqual(self.wallet.balance, 10)
        self.assertEqual(self.wallet.locked, 0)
        self.assertEqual(self.system_wallet.balance, -10)
