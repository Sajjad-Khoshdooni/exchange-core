from django.db import models

from ledger.requester.address_requester import AddressRequester
from ledger.models.address_key import AddressKey, ARCHITECTURE_OF_NETWORK


class DepositAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)
    address_key = models.ForeignKey('ledger.AddressKey', on_delete=models.PROTECT)

    def __str__(self):
        return '%s (network= %s)' % (self.address, self.network)

    @classmethod
    def get_deposit_address(cls, account, network):
        if DepositAddress.objects.filter(address_key__account=account, network=network).exists():
            return DepositAddress.objects.get(address_key__account=account, network=network)

        elif not AddressKey.objects.filter(account=account, architecture=ARCHITECTURE_OF_NETWORK.get(network)).exists():
            address_dictionary = AddressRequester().create_wallet(account, ARCHITECTURE_OF_NETWORK.get(network))
            address_key = AddressKey.objects.create(
                account=account,
                address=address_dictionary.get('pointer_address'),
                public_address=address_dictionary.get('public_address')
            )

        else:
            address_key = AddressKey.objects.get(account=account)

        deposit_address = DepositAddress.objects.create(
            network=network,
            address_key=address_key,
            address=address_key.public_address,
        )

        return deposit_address

    def update_transaction_history(self):
        from ledger.requester.trx_history_updater import UpdateTrxHistory
        UpdateTrxHistory().update_history(deposit_address=self)

    class Meta:
        unique_together = (
            ('network', 'address'),
        )
