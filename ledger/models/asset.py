from django.db import models
from rest_framework import serializers

from accounts.models import Account


class Asset(models.Model):
    IRT = 'IRT'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)
    image = models.FileField(upload_to='asset-logo/')

    def get_wallet(self, account: Account):
        from ledger.models import Wallet

        wallet, _ = Wallet.objects.get_or_create(
            asset=self,
            account=account,
            defaults={
                'balance': 0
            }
        )

        return wallet

    @classmethod
    def get(cls, symbol: str):
        return Asset.objects.get(symbol=symbol)


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol', 'name', 'name_fa', 'image')


class AssetSerializerMini(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol')
