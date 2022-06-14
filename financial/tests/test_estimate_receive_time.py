import datetime
from uuid import uuid4

from django.test import TestCase

from accounts.models import Account
from financial.utils.test import new_user, new_bank_account, new_fiat_withdraw_request
from financial.utils.withdraw_limit import get_fiat_estimate_receive_time
from ledger.models import Asset, Trx


class EstimateReceiveTimeTestCase(TestCase):

    def setUp(self):
        self.user_1 = new_user()
        self.bank_account = new_bank_account(self.user_1)
        self.IRT = Asset.get(Asset.IRT)

        Trx.transaction(
            group_id=uuid4(),
            sender=self.IRT.get_wallet(Account.system()),
            receiver=self.IRT.get_wallet(self.user_1.account),
            amount=1000000000,
            scope=Trx.TRANSFER
        )

    def test_estimate_receive_time(self):

        wallet = self.IRT.get_wallet(self.user_1.account)
        amount = 100000
        fiat_withdraw_1 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2020, 5, 17, 0, 10).astimezone(),
        )
        fiat_withdraw_2 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2020, 5, 17, 9, 10).astimezone(),
        )
        fiat_withdraw_3 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2020, 5, 17, 12, 0).astimezone(),
        )
        fiat_withdraw_4 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2020, 5, 17, 15, 10).astimezone(),
        )
        fiat_withdraw_5 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2020, 5, 17, 20, 0).astimezone(),
        )
        fiat_withdraw_6 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2022, 5, 19, 20, 0).astimezone(),
        )
        fiat_withdraw_7 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2022, 5, 20, 8, 10).astimezone(),
        )
        fiat_withdraw_8 = new_fiat_withdraw_request(
            amount=amount,
            wallet=wallet,
            bank_account=self.bank_account,
            datetime=datetime.datetime(2022, 5, 20, 12, 10).astimezone(),
        )

        self.assertEqual(
            datetime.datetime(2020, 5, 17, 10, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_1.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2020, 5, 17, 14, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_2.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2020, 5, 17, 19, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_3.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2020, 5, 18, 4, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_4.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2020, 5, 18, 10, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_5.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2022, 5, 20, 14, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_6.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2022, 5, 20, 15, 0).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_7.withdraw_datetime).astimezone()
        )
        self.assertEqual(
            datetime.datetime(2022, 5, 21, 10, 30).astimezone(),
            get_fiat_estimate_receive_time(fiat_withdraw_8.withdraw_datetime).astimezone()
        )
