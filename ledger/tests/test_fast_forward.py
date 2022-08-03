from django.test import TestCase
from decimal import Decimal

from ledger.utils.test import new_account, new_network
from ledger.models import Transfer, DepositAddress, Trx, Asset, AddressKey

from ledger.requester.withdraw_requester import RequestWithdraw


class FastForwardTestCase(TestCase):
    def setUp(self) -> None:
        self.network = new_network()
        self.asset = Asset.objects.create(symbol=self.network.symbol)

        self.sender_account1 = new_account()
        self.sender_address_key1 = AddressKey.objects.create(account=self.sender_account1, address='0xC8E19189888BED6aaBf88800024106eC7C8cb00B')
        self.sender_deposit_address1 = DepositAddress.objects.create(
            # account=self.sender_account1,
            network=self.network,
            address_key=self.sender_address_key1,
            address='0xC8E19189888BED6aaBf88800024106eC7C8cb00B'
        )
        self.sender_wallet1 = self.asset.get_wallet(account=self.sender_account1)
        self.sender_wallet1.balance = 10
        self.sender_wallet1.save()

        self.receiver_account1 = new_account()
        self.receiver_address_key1 = AddressKey.objects.create(account=self.receiver_account1, address='0x701e0e2f85E3922F50C054d113b9D694c675a7f5')
        self.receiver_deposit_address1 = DepositAddress.objects.create(
            # account=self.receiver_account1,
            network=self.network,
            address_key=self.receiver_address_key1,
            address='0x701e0e2f85E3922F50C054d113b9D694c675a7f5'
        )
        self.receiver_wallet1 = self.asset.get_wallet(account=self.receiver_account1)


        # self.sender_account2 = new_account()
        # self.sender_address_key2 = AddressKey.objects.create(account=self.sender_account2, address='0x3e14933d732f4197B4AA82D0D91286BEb8Ac31E9')
        # self.sender_deposit_address2 = DepositAddress.objects.create(
        #     account=self.sender_account2,
        #     network=self.network,
        #     address_key=self.sender_address_key2,
        #     address='0x3e14933d732f4197B4AA82D0D91286BEb8Ac31E9'
        # )
        # self.sender_wallet2 = self.asset.get_wallet(account=self.sender_account2)
        #
        #
        # self.receiver_account2 = new_account()
        # self.receiver_address_key2 = AddressKey.objects.create(account=self.receiver_account2, address='0xC40e9B5d702B0e698506fbE49df6504773f850e0')
        # self.receiver_deposit_address2 = DepositAddress.objects.create(
        #     account=self.receiver_account2,
        #     network=self.network,
        #     address_key=self.receiver_address_key2,
        #     address='0xC40e9B5d702B0e698506fbE49df6504773f850e0'
        # )
        # self.receiver_wallet2 = self.asset.get_wallet(account=self.receiver_account2)

    def test_fast_forward1(self):
        Transfer.check_fast_forward(
            sender_wallet=self.sender_wallet1,
            network=self.network,
            amount=Decimal(1),
            address=self.receiver_deposit_address1.address
        )

        self.assertEqual(
            Trx.objects.get(sender=self.sender_wallet1).group_id,
            Transfer.objects.get(deposit_address=self.receiver_deposit_address1).group_id)

    def test_fast_forward2(self):
        transfer = Transfer.check_fast_forward(
            sender_wallet=self.sender_wallet1,
            network=self.network,
            amount=Decimal(1),
            address='0x6D3251369E08248f7a37355E497682Fd465767fb'
        )

        self.assertEqual(transfer, None)
#
