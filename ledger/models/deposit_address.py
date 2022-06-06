from django.db import models

from ledger.address_requester import AddressRequester


class DepositAddress(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True) # in base 16 e vali byd base 58 bashe

    def __str__(self):
        return '%s %s (network= %s)' % (self.account_secret, self.address, self.network)


    @classmethod
    def new_deposit_address(cls, account, network):
        address = AddressRequester.create_wallet(account=account)

        return DepositAddress.objects.create(
            network=network,
            account=account,
            address=address,
        )

    @property
    def account(self):
        return self.account

    class Meta:
        unique_together = (
            ('network', 'account'),
            ('network', 'address'),
        )
