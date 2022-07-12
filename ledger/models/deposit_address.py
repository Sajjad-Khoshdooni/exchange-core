from django.db import models

from ledger.requester.address_requester import AddressRequester
from ledger.models.address_key import AddressKey
from ledger.requester.register_address_requester import RegisterAddress


class DepositAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)
    is_registered = models.BooleanField(default=False)
    address_key = models.OneToOneField('ledger.AddressKey', on_delete=models.PROTECT, unique=True)

    def __str__(self):
        return '%s (network= %s)' % (self.address, self.network)

    @classmethod
    def get_deposit_address(cls, account, network):
        address, address_key = None, None

        if DepositAddress.objects.filter(address_key__account=account, network=network).exists():
            return DepositAddress.objects.get(address_key__account=account, network=network)

        elif not AddressKey.objects.filter(account=account).exists():
            address = AddressRequester().create_wallet()
            address_key = AddressKey.objects.create(
                account=account,
                address=address
            )
        else:
            address_key = AddressKey.objects.get(account=account)
            address = AddressRequester().generate_public_address(network=network.symbol, address=address_key.address)

        deposit_address = DepositAddress.objects.create(
            network=network,
            address_key=address_key,
            address=address,
        )
        RegisterAddress().register(deposit_address)

        return deposit_address

    class Meta:
        unique_together = (
            ('network', 'address'),
        )
