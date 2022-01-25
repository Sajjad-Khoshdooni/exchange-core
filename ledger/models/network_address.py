from django.db import models, transaction
from rest_framework import serializers

from ledger.models.network import NetworkSerializer
from ledger.utils.address import get_network_address


class NetworkAddress(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT)
    address = models.CharField(max_length=256, blank=True, unique=True)
    # address_tag = models.CharField(max_length=32, blank=True)

    def __str__(self):
        return '%s %s (%s)' % (self.account, self.network, self.address)

    def save(self, *args, **kwargs):

        if not self.pk:
            self.address = ''
            super().save(*args, **kwargs)
            self.address = get_network_address(self.network.symbol.lower(), self.pk)
            self.save()

        else:
            super().save(*args, **kwargs)

    class Meta:
        unique_together = ('network', 'account')


class NetworkAddressSerializer(serializers.ModelSerializer):
    network = serializers.SerializerMethodField()

    def get_network(self, network_address: NetworkAddress):
        return network_address.network.symbol

    class Meta:
        model = NetworkAddress
        fields = ('network', 'address')
