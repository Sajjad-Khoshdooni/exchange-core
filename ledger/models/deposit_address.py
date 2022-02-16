from django.db import models

from ledger.models import AccountSecret


class DepositAddress(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account_secret = models.ForeignKey('ledger.AccountSecret', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True)

    # address_tag = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return '%s %s (network= %s)' % (self.account_secret, self.address, self.network)

    @property
    def presentation_address(self):
        wallet = self.account_secret.get_crypto_wallet(self.network)
        return wallet.get_presentation_address(self.address)

    @classmethod
    def new_deposit_address(cls, account, network):
        account_secret, _ = AccountSecret.objects.get_or_create(account=account)
        crypto_wallet = account_secret.get_crypto_wallet(network)

        return DepositAddress.objects.create(
            network=network,
            account_secret=account_secret,
            address=crypto_wallet.address,
        )

    @property
    def account(self):
        return self.account_secret.account

    class Meta:
        unique_together = (
            ('network', 'account_secret'),
            ('network', 'address'),
        )
