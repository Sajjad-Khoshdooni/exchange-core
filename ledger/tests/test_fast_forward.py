from decimal import Decimal
from unittest import mock

from django.test import TestCase

from ledger.models import Transfer, DepositAddress, Trx, Asset, AddressKey, Network
from ledger.utils.test import new_account, set_price


class FastForwardTestCase(TestCase):
    def new_network(self) -> Network:
        symbol = 'ETH'
        name = 'ETH'
        address_regex = '[1-9]'
        network = Network.objects.create(symbol=symbol, name=name, address_regex=address_regex)

        return network

    def setUp(self) -> None:
        self.network = self.new_network()
        self.asset, _ = Asset.objects.get_or_create(symbol=self.network.symbol)
        set_price(self.asset, 19000)

        self.sender_account1 = new_account()
        self.sender_address_key1 = AddressKey.objects.create(account=self.sender_account1, address='0xC8E19189888BED6aaBf88800024106eC7C8cb00B', architecture='ETH')
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
        self.receiver_address_key1 = AddressKey.objects.create(account=self.receiver_account1, address='0x701e0e2f85E3922F50C054d113b9D694c675a7f5', architecture='ETH')
        self.receiver_deposit_address1 = DepositAddress.objects.create(
            # account=self.receiver_account1,
            network=self.network,
            address_key=self.receiver_address_key1,
            address='0x701e0e2f85E3922F50C054d113b9D694c675a7f5'
        )
        self.receiver_wallet1 = self.asset.get_wallet(account=self.receiver_account1)

    @mock.patch('ledger.models.deposit_address.request_architecture')
    def test_fast_forward1(self, request_architecture):
        request_architecture.return_value = 'ETH'

        Transfer.check_fast_forward(
            sender_wallet=self.sender_wallet1,
            network=self.network,
            amount=Decimal(1),
            address=self.receiver_deposit_address1.address
        )

        self.assertEqual(
            Trx.objects.get(sender=self.sender_wallet1).group_id,
            Transfer.objects.get(deposit_address=self.receiver_deposit_address1).group_id)

    @mock.patch('ledger.models.deposit_address.request_architecture')
    def test_fast_forward2(self, request_architecture):
        request_architecture.return_value = 'ETH'
        print(request_architecture('BSC'))

        transfer = Transfer.check_fast_forward(
            sender_wallet=self.sender_wallet1,
            network=self.network,
            amount=Decimal(1),
            address='0x6D3251369E08248f7a37355E497682Fd465767fb'
        )

        self.assertEqual(transfer, None)

