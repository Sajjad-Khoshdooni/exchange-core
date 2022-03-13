from decimal import Decimal

from django.db import models
from rest_framework import serializers

from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.precision import get_precision, get_presentation_amount
from django.core.validators import MaxValueValidator, MinValueValidator


class InvalidAmount(Exception):
    pass


class LiveAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enable=True)


class Asset(models.Model):
    IRT = 'IRT'
    USDT = 'USDT'
    SHIB = 'SHIB'

    HEDGE_BINANCE_FUTURE = 'binance-future'
    HEDGE_BINANCE_SPOT = 'binance-spot'

    objects = models.Manager()
    live_objects = LiveAssetManager()

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True, db_index=True)

    trade_quantity_step = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    min_trade_quantity = models.DecimalField(max_digits=15, decimal_places=10, default='0.000001')
    max_trade_quantity = models.DecimalField(max_digits=18, decimal_places=2, default=1e9)

    price_precision_usdt = models.SmallIntegerField(default=2)
    price_precision_irt = models.SmallIntegerField(default=0)
    precision = models.SmallIntegerField(default=0)

    enable = models.BooleanField(default=False)
    order = models.SmallIntegerField(default=0, db_index=True)

    trend = models.BooleanField(default=False)
    pin_to_top = models.BooleanField(default=False)

    hedge_method = models.CharField(max_length=16, default=HEDGE_BINANCE_FUTURE, choices=[
        (HEDGE_BINANCE_FUTURE, HEDGE_BINANCE_FUTURE), (HEDGE_BINANCE_SPOT, HEDGE_BINANCE_SPOT),
    ])

    bid_diff = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=4, validators=[
        MinValueValidator(0),
        MaxValueValidator(Decimal('0.1')),
    ], help_text='our bid (taker sell price) = (1 - bid_diff) * binance_bid')

    ask_diff = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=4, validators=[
        MinValueValidator(0),
        MaxValueValidator(Decimal('0.1')),
    ], help_text='our ask (taker buy price) = (1 + ask_diff) * binance_ask')

    class Meta:
        ordering = ('-pin_to_top', '-trend', 'order', )

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
        return get_presentation_amount(amount, self.precision)

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

    trade_precision = serializers.SerializerMethodField()

    def get_trade_precision(self, asset: Asset):
        return get_precision(asset.trade_quantity_step)

    class Meta:
        model = Asset
        fields = ('symbol', 'trade_precision')
