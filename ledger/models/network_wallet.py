import uuid

from django.db import models


class NetworkWallet(models.Model):
    network_asset = models.ForeignKey('ledger.NetworkAsset', on_delete=models.PROTECT)
    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT)
    address = models.CharField(max_length=256)
    address_tag = models.CharField(max_length=32, default='')

    class Meta:
        unique_together = ('network_asset', 'wallet')
