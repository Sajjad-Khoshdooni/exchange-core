from django.db import models

from ledger.requester.address_requester import AddressRequester
from ledger.models.address_key import AddressKey
from ledger.requester.architecture_requester import request_architecture


class DepositAddress(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)
    address_key = models.ForeignKey('ledger.AddressKey', on_delete=models.PROTECT)

    def __str__(self):
        return '%s (network= %s)' % (self.address, self.network)

    @classmethod
    def get_deposit_address(cls, account, network):
        architecture = request_architecture(network)

        address_key = AddressKey.objects.filter(account=account, architecture=architecture, deleted=False).first()

        if not address_key:
            address_dict = AddressRequester().create_wallet(account, architecture)

            address_key = AddressKey.objects.create(
                account=account,
                address=address_dict.get('pointer_address'),
                public_address=address_dict.get('public_address'),
                architecture=architecture
            )

        deposit_address = DepositAddress.objects.filter(address_key=address_key, network=network).first()

        if not deposit_address:
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
            ('network', 'address_key'),
        )
