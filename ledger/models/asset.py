from datetime import datetime
from decimal import Decimal
from typing import Union

from django.conf import settings
from django.db import models
from rest_framework import serializers

from _base.settings import SYSTEM_ACCOUNT_ID
from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.precision import get_precision, get_presentation_amount


class InvalidAmount(Exception):
    pass


class LiveAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enable=True)


class Asset(models.Model):
    IRT = 'IRT'
    USDT = 'USDT'
    SHIB = 'SHIB'

    PRECISION = 8

    objects = models.Manager()
    live_objects = LiveAssetManager()

    name = models.CharField(max_length=32, blank=True)
    name_fa = models.CharField(max_length=32, blank=True)
    original_name_fa = models.CharField(max_length=32, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=16, unique=True, db_index=True)
    original_symbol = models.CharField(max_length=16, blank=True)

    trade_quantity_step = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    min_trade_quantity = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    max_trade_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=1e9)

    price_precision_usdt = models.SmallIntegerField(default=2)
    price_precision_irt = models.SmallIntegerField(default=0)

    enable = models.BooleanField(default=False)
    order = models.SmallIntegerField(default=0, db_index=True)

    trend = models.BooleanField(default=False)
    pin_to_top = models.BooleanField(default=False)

    trade_enable = models.BooleanField(default=True)
    hedge = models.BooleanField(default=True)

    margin_enable = models.BooleanField(default=False)
    spread_category = models.ForeignKey('ledger.AssetSpreadCategory', on_delete=models.PROTECT, null=True, blank=True)
    new_coin = models.BooleanField(default=False)

    class Meta:
        ordering = ('-pin_to_top', '-trend', 'order', )

    def __str__(self):
        return self.symbol

    def get_precision(self):
        if self.symbol == Asset.IRT:
            return 0
        else:
            return Asset.PRECISION

    def get_wallet(self, account: Union[Account, int], market: str = Wallet.SPOT, variant: str = None,
                   expiration: datetime = None):
        assert market in Wallet.MARKETS

        if isinstance(account, int):
            account_filter = {'account_id': account}

            if account == SYSTEM_ACCOUNT_ID:
                account_type = Account.SYSTEM
            else:
                account_type = Account.ORDINARY

        elif isinstance(account, Account):
            account_filter = {'account': account}
            account_type = account.type
        else:
            raise NotImplementedError

        wallet, created = Wallet.objects.get_or_create(
            asset=self,
            market=market,
            variant=variant,
            **account_filter,
            defaults={
                'check_balance': account_type == Account.ORDINARY,
                'expiration': expiration
            }
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
        return get_presentation_amount(amount, self.get_precision())

    def get_presentation_price_irt(self, price: Decimal) -> str:
        return get_presentation_amount(price, self.price_precision_irt)

    def get_presentation_price_usdt(self, price: Decimal) -> str:
        return get_presentation_amount(price, self.price_precision_usdt)

    @property
    def future_symbol(self):
        if self.symbol == 'SHIB':
            return '1000SHIB'
        else:
            return self.symbol


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', 'trade_quantity_step', 'min_trade_quantity', 'max_trade_quantity')


class AssetSerializerMini(serializers.ModelSerializer):
    precision = serializers.SerializerMethodField()
    step_size = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    original_name_fa = serializers.SerializerMethodField()
    original_symbol = serializers.SerializerMethodField()

    def get_precision(self, asset: Asset):
        return asset.get_precision()

    def get_step_size(self, asset: Asset):
        return get_precision(asset.trade_quantity_step)

    def get_logo(self, asset: Asset):
        return settings.MINIO_STORAGE_STATIC_URL + '/coins/%s.png' % asset.symbol

    def get_original_symbol(self, asset: Asset):
        return asset.original_symbol or asset.symbol

    def get_original_name_fa(self, asset: Asset):
        return asset.original_name_fa or asset.name_fa

    class Meta:
        model = Asset
        fields = ('symbol', 'margin_enable', 'precision', 'step_size', 'name', 'name_fa', 'logo', 'original_symbol',
                  'original_name_fa')


class CoinField(serializers.CharField):
    def to_representation(self, value: Asset):
        if value:
            return value.symbol

    def to_internal_value(self, data: str):
        if not data:
            return
        else:
            return Asset.get(symbol=data)
