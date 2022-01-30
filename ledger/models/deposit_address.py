from django.db import models, transaction
from rest_framework import serializers

from accounts.models import Account
from ledger.models import AccountSecret
from ledger.utils.address import get_network_address
from wallet.models import Secret


class DepositAddress(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account_secret = models.ForeignKey('ledger.AccountSecret', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True, unique=True)

    # address_tag = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return '%s %s (network= %s)' % (self.account_secret, self.address, self.network)

    @classmethod
    def new_deposit_address(cls, account, network):
        account_secret, _ = AccountSecret.objects.get_or_create(account=account)
        secret = account_secret.secret
        secret.__class__ = secret.get_secret_wallet(network.symbol)

        return DepositAddress.objects.create(
            network=network,
            account_secret=account_secret,
            address=secret.address,
        )

    @property
    def account(self):
        return self.account_secret.account

    class Meta:
        unique_together = ('network', 'account_secret')
