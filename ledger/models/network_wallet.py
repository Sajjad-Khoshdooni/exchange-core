from django.db import models
from rest_framework import serializers

from ledger.models.network import NetworkSerializer


class NetworkWallet(models.Model):
    network = models.ForeignKey('ledger.Network', on_delete=models.PROTECT)
    wallet = models.ForeignKey('ledger.Wallet', on_delete=models.PROTECT, related_name='networks')
    address = models.CharField(max_length=256)
    address_tag = models.CharField(max_length=32, default='')

    def __str__(self):
        return '%s - %s' % (self.network, self.wallet)

    class Meta:
        unique_together = ('network', 'wallet')


class NetworkWalletSerializer(serializers.ModelSerializer):
    network = NetworkSerializer()

    class Meta:
        model = NetworkWallet
        fields = '__all__'
