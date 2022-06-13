from django.db import models

from ledger.requester.address_requester import AddressRequester


class DepositAddress(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)
    is_registered = models.BooleanField(default=False)

    def __str__(self):
        return '%s (network= %s)' % (self.address, self.network)


    @classmethod
    def new_deposit_address(cls, account, network):
        # if DepositAddress.objects.filter(account=account, network=network).exists():
        #     return DepositAddress.objects.get(account=account, network=network)

        address = AddressRequester().create_wallet(network_symbol=network.symbol)

        return DepositAddress.objects.create(
            network=network,
            # account=account,
            address=address,
        )

    @property
    def account(self):
        return self.account

    class Meta:
        unique_together = (
            # ('network', 'account'),
            ('network', 'address'),
        )
