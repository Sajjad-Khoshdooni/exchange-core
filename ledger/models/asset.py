import math
from decimal import Decimal

from django.db import models
from rest_framework import serializers

from accounts.models import Account


class InvalidAmount(Exception):
    pass


class Asset(models.Model):
    IRT = 'IRT'

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True, db_index=True)

    trade_quantity_step = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    min_trade_quantity = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    max_trade_quantity = models.DecimalField(max_digits=15, decimal_places=5, default=1e9)

    def __str__(self):
        return self.symbol

    def get_wallet(self, account: Account):
        from ledger.models import Wallet

        wallet, _ = Wallet.objects.get_or_create(
            asset=self,
            account=account,
            defaults={
            }
        )

        return wallet

    @classmethod
    def get(cls, symbol: str):
        return Asset.objects.get(symbol=symbol)

    def is_cash(self):
        return self.symbol == self.IRT

    def is_coin(self):
        return not self.is_cash()

    def is_trade_amount_valid(self, amount: Decimal, raise_exception: bool = False):
        if raise_exception:
            reason = None
            if amount < self.min_trade_quantity:
                raise InvalidAmount('واحد وارد شده کوچک است.')
            elif amount > self.max_trade_quantity:
                raise InvalidAmount('واحد وارد شده بزرگ است.')
            elif amount % self.trade_quantity_step != 0:
                raise InvalidAmount('واحد وارد شده باید مضربی از %s باشد.' % self.get_presentation_amount(self.trade_quantity_step))

        else:
            return \
                self.min_trade_quantity <= amount <= self.max_trade_quantity and \
                amount % self.trade_quantity_step == 0

    def get_presentation_amount(self, amount: Decimal) -> str:
        if isinstance(amount, str):
            amount = Decimal(amount)

        n_digits = int(-math.log10(Decimal(self.trade_quantity_step)))
        rounded = round(amount, n_digits)
        return str(rounded).rstrip('0').rstrip('.') or '0'


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', 'trade_quantity_step', 'min_trade_quantity', 'max_trade_quantity')


class AssetSerializerMini(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', )
