# from django.test import TestCase
# from decimal import Decimal
#
# from ledger.utils.test import new_account, new_network
# from ledger.models import Transfer, DepositAddress, Trx, Asset
#
# from ledger.requester.withdraw_requester import RequestWithdraw
#
#
# class FastForwardTestCase(TestCase):
#     def setUp(self) -> None:
#         self.sender_account1 = new_account()
#         self.receiver_account1 = new_account()
#
#         self.sender_account2 = new_account()
#         self.receiver_account2 = new_account()
#
#         self.network = new_network()
#         self.asset = Asset.objects.create(symbol=self.network.symbol)
#
#         self.sender_deposit_address1 = DepositAddress.get_deposit_address(
#             account=self.sender_account1,
#             network=self.network)
#         self.sender_wallet1 = self.asset.get_wallet(account=self.sender_account1)
#
#         self.sender_deposit_address2 = DepositAddress.get_deposit_address(
#             account=self.sender_account2,
#             network=self.network)
#         self.sender_wallet2 = self.asset.get_wallet(account=self.sender_account2)
#
#         self.receiver_deposit_address1 = DepositAddress.get_deposit_address(
#             account=self.receiver_account1,
#             network=self.network
#         )
#         self.receiver_wallet1 = self.asset.get_wallet(account=self.receiver_account1)
#
#         self.receiver_deposit_address2 = DepositAddress.get_deposit_address(
#             account=self.receiver_account2,
#             network=self.network
#         )
#         self.receiver_wallet2 = self.asset.get_wallet(account=self.receiver_account2)
#
#         RequestWithdraw().withdraw_from_hot_wallet(
#             receiver_address=self.sender_deposit_address1.address,
#             amount=0.01,
#             network=self.network.symbol,
#             asset='BNB',
#             transfer_id=1
#         )
#
#     def test_fast_forward1(self):
#         Transfer.new_withdraw(
#             wallet=self.sender_wallet1,
#             network=self.network,
#             amount=Decimal(0),
#             address=self.receiver_deposit_address1.address
#         )
#
#         self.assertEqual(
#             Trx.objects.get(sender=self.sender_wallet1).group_id,
#             Transfer.objects.get(deposit_address=self.receiver_deposit_address1).group_id)
#
#     def test_fast_forward2(self):
#         Transfer.new_withdraw(
#             wallet=self.sender_wallet2,
#             network=self.network,
#             amount=Decimal(0),
#             address=self.receiver_deposit_address2.address
#         )
#
#         self.assertEqual(
#             Trx.objects.get(sender=self.sender_wallet2).group_id,
#             None
#         )
#
