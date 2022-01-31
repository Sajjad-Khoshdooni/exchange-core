import math
from decimal import Decimal

from django.db import models
from rest_framework import serializers

from accounts.models import Account
from ledger.models import Wallet


class InvalidAmount(Exception):
    pass


class LiveAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enable=True).order_by('order')


class Asset(models.Model):
    IRT = 'IRT'
    USDT = 'USDT'

    live_objects = LiveAssetManager()
    objects = models.Manager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True, db_index=True)

    trade_quantity_step = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    min_trade_quantity = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    max_trade_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=1e9)

    price_precision_usdt = models.SmallIntegerField(default=2)
    price_precision_irt = models.SmallIntegerField(default=0)

    enable = models.BooleanField(default=False)
    order = models.SmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ('order', )

    def __str__(self):
        return self.symbol

    def get_wallet(self, account: Account, market: str = Wallet.SPOT):
        assert market in Wallet.MARKETS

        wallet, _ = Wallet.objects.get_or_create(
            asset=self,
            account=account,
            market=market,
        )

        return wallet

    @classmethod
    def get(cls, symbol: str):
        return Asset.objects.get(symbol=symbol)

    def is_cash(self):
        return self.symbol == self.IRT

    def is_trade_base(self):
        return self.symbol in (self.IRT, self.USDT)

    def is_trade_amount_valid(self, amount: Decimal, raise_exception: bool = False):
        if raise_exception:
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
        rounded = str(round(amount, n_digits))

        if '.' not in rounded:
            return rounded
        else:
            return rounded.rstrip('0').rstrip('.') or '0'


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', 'trade_quantity_step', 'min_trade_quantity', 'max_trade_quantity')


class AssetSerializerMini(serializers.ModelSerializer):

    class Meta:
        model = Asset
        fields = ('symbol', )
