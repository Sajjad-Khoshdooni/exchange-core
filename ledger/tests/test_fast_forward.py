from django.test import TestCase
from decimal import Decimal

from ledger.utils.test import new_account, new_network
from ledger.models import Transfer, DepositAddress, Trx, Asset

from ledger.requester.withdraw_requester import RequestWithdraw


class FastForwardTestCase(TestCase):
    def setUp(self) -> None:
        self.sender_account = new_account()
        self.receiver_account = new_account()
        self.network = new_network()
        self.asset = Asset.objects.create(symbol=self.network.symbol)
        self.sender_deposit_address = DepositAddress.get_deposit_address(
            account=self.sender_account,
            network=self.network)
        self.sender_wallet = self.asset.get_wallet(account=self.sender_account)
        self.receiver_deposit_address = DepositAddress.get_deposit_address(
            account=self.receiver_account,
            network=self.network)
        self.receiver_wallet = self.asset.get_wallet(account=self.receiver_account)

        RequestWithdraw().withdraw_from_hot_wallet(
            receiver_address=self.sender_deposit_address.address,
            amount=0.01,
            network=self.network.symbol,
            asset='BNB',
            requester_id=1
        )

    def test_fast_forward2(self):
        Transfer.new_withdraw(
            wallet=self.sender_wallet,
            network=self.network,
            amount=Decimal(0),
            address=self.receiver_deposit_address.address)

        self.assertEqual(
            Trx.objects.get(sender=self.sender_wallet).group_id,
            Transfer.objects.get(deposit_address=self.receiver_deposit_address).group_id)
