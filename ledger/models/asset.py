from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from rest_framework import serializers

from _base.settings import SYSTEM_ACCOUNT_ID
from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.precision import get_precision, get_presentation_amount
from provider.exchanges.interface.binance_interface import ExchangeHandler


class InvalidAmount(Exception):
    pass


class LiveAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enable=True)


class CandidAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(enable=False, candidate=False)


class Asset(models.Model):
    IRT = 'IRT'
    USDT = 'USDT'
    SHIB = 'SHIB'

    HEDGE_NONE = ''
    HEDGE_BINANCE_FUTURE = 'binance-future'
    HEDGE_BINANCE_SPOT = 'binance-spot'

    HEDGE_KUCOIN_FUTURE = 'kucoin-future'
    HEDGE_KUCOIN_SPOT = 'kucoin-spot'

    HEDGE_METHOD_CHOICE = (
        (HEDGE_KUCOIN_SPOT, HEDGE_KUCOIN_SPOT),
        (HEDGE_KUCOIN_FUTURE, HEDGE_KUCOIN_FUTURE),
        (HEDGE_BINANCE_SPOT, HEDGE_BINANCE_SPOT),
        (HEDGE_BINANCE_FUTURE, HEDGE_BINANCE_FUTURE),
        (HEDGE_NONE, HEDGE_NONE)
    )
    PRECISION = 8

    objects = models.Manager()
    live_objects = LiveAssetManager()
    candid_objects = CandidAssetManager()

    name = models.CharField(max_length=32, blank=True)
    name_fa = models.CharField(max_length=32, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=16, unique=True, db_index=True)

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

    hedge_method = models.CharField(max_length=32, default=HEDGE_BINANCE_FUTURE, choices=HEDGE_METHOD_CHOICE)

    candidate = models.BooleanField(default=False)

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

    def get_wallet(self, account: Account, market: str = Wallet.SPOT, variant: str = None):
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

        wallet, _ = Wallet.objects.get_or_create(
            asset=self,
            market=market,
            variant=variant,
            **account_filter,
            defaults={
                'check_balance': account_type == Account.ORDINARY
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

    def get_hedger(self) -> ExchangeHandler:
        return ExchangeHandler.get_handler(name=self.hedge_method)


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', 'trade_quantity_step', 'min_trade_quantity', 'max_trade_quantity')


class AssetSerializerMini(serializers.ModelSerializer):
    precision = serializers.SerializerMethodField()
    step_size = serializers.SerializerMethodField()

    def get_precision(self, asset: Asset):
        return asset.get_precision()

    def get_step_size(self, asset: Asset):
        return get_precision(asset.trade_quantity_step)

    class Meta:
        model = Asset
        fields = ('symbol', 'margin_enable', 'precision', 'step_size', 'name', 'name_fa', 'logo')


class CoinField(serializers.CharField):
    def to_representation(self, value: Asset):
        if value:
            return value.symbol

    def to_internal_value(self, data: str):
        if not data:
            return
        else:
            return Asset.get(symbol=data)

