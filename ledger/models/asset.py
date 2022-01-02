from decimal import Decimal

from django.db import models
from rest_framework import serializers

from account.models import Account


class Asset(models.Model):
    IRT = 'IRT'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)
    image = models.FileField(upload_to='asset-logo/')

    trade_quantity_step = models.DecimalField(max_digits=15, decimal_places=5, default=1)
    min_trade_quantity = models.DecimalField(max_digits=15, decimal_places=5, default=0)
    max_trade_quantity = models.DecimalField(max_digits=15, decimal_places=5, default=1e9)

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

    def is_trade_amount_valid(self, amount: Decimal):
        return self.min_trade_quantity <= amount <= self.max_trade_quantity and amount % self.trade_quantity_step == 0


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol', 'name', 'name_fa', 'image', 'trade_quantity_step', 'min_trade_quantity',
                  'max_trade_quantity')


class AssetSerializerMini(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol')
