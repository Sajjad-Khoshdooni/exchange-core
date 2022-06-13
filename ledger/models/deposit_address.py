from django.db import models

from ledger.requester.address_requester import AddressRequester
from ledger.models.address_key import AddressKey
from wallet.utils import get_base58_address


class DepositAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)
    is_registered = models.BooleanField(default=False)
    address_key = models.ForeignKey('ledger.address_key', on_delete=models.PROTECT, unique=True)

    def __str__(self):
        return '%s (network= %s)' % (self.address, self.network)

    @classmethod
    def new_deposit_address(cls, account, network):
        if DepositAddress.objects.filter(address_key__account=account).exists():
            return DepositAddress.objects.get(address_key__account=account)

        address = AddressRequester().create_wallet(network_symbol=network.symbol)
        address_key = AddressKey.objects().create(
            account=account,
            address=address
        )

        return DepositAddress.objects.create(
            network=network,
            address_key=address_key,
            address=get_presentation_address(network=network, base16_address=address),
        )

    @property
    def account(self):
        return self.account

    class Meta:
        unique_together = (
            ('network', 'address'),
        )


def get_presentation_address(network, base16_address):
    if network == 'BSC' or network == 'ETH':
        return base16_address
    elif network == 'TRX':
        return get_base58_address('41' + base16_address)
