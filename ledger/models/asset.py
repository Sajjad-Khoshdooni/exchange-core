from datetime import datetime
from decimal import Decimal
from typing import Union

from django.conf import settings
from django.db import models
from django.db.models import Min, Max
from rest_framework import serializers

from _base.settings import SYSTEM_ACCOUNT_ID, OTC_ACCOUNT_ID
from accounts.models import Account
from ledger.models import Wallet
from ledger.utils.external_price import BUY, SELL, get_external_usdt_prices, get_external_price
from ledger.utils.precision import get_presentation_amount
from ledger.utils.fields import get_amount_field

class InvalidAmount(Exception):
    pass


class LiveAssetManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(enable=True)


class Asset(models.Model):
    IRT = 'IRT'
    USDT = 'USDT'
    SHIB = 'SHIB'

    ACTIVE, DISABLED = 'active', 'disabled'

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

    enable = models.BooleanField(default=False)
    order = models.SmallIntegerField(default=0, db_index=True)

    trend = models.BooleanField(default=False)
    pin_to_top = models.BooleanField(default=False)

    trade_enable = models.BooleanField(default=True)
    hedge = models.BooleanField(default=True)

    margin_enable = models.BooleanField(default=False)
    spread_category = models.ForeignKey('ledger.AssetSpreadCategory', on_delete=models.SET_NULL, null=True, blank=True)

    publish_date = models.DateTimeField(null=True, blank=True)

    otc_status = models.CharField(
        max_length=8,
        default=ACTIVE,
        choices=((ACTIVE, ACTIVE), (BUY, BUY), (SELL, SELL), (DISABLED, DISABLED)),
    )

    price_page = models.BooleanField(default=False)

    price_alert_chanel_sensitivity = get_amount_field(null=True)

    distribution_factor = models.FloatField(default=0)

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

            if account in (SYSTEM_ACCOUNT_ID, OTC_ACCOUNT_ID):
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
                'expiration': expiration,
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

    def get_original_symbol(self):
        return self.original_symbol or self.symbol

    def get_coin_multiplier(self) -> int:
        if not self.original_symbol or self.symbol == self.original_symbol:
            return 1
        elif self.symbol.startswith('1M-'):
            return 10 ** 6
        elif self.symbol.startswith('1000'):
            return 10 ** 3
        else:
            return 1

    @property
    def future_symbol(self):
        if self.symbol == 'SHIB':
            return '1000SHIB'
        else:
            return self.symbol

    @staticmethod
    def get_current_prices(coins, allow_stale: bool = False):
        prices = get_external_usdt_prices(
            coins=coins,
            side=SELL,
            apply_otc_spread=True,
            allow_stale=allow_stale
        )
        market_prices = {}
        from market.models import Order
        for base_asset in ('IRT', 'USDT'):
            market_prices[base_asset] = {
                o['symbol__name'].replace(base_asset, ''): o['best_ask'] for o in Order.open_objects.filter(
                    side=SELL,
                    symbol__enable=True,
                    symbol__name__in=map(lambda s: f'{s}{base_asset}', coins)
                ).values('symbol__name').annotate(best_ask=Min('price'))
            }
        market_prices['USDT']['IRT'] = Decimal(1) / Order.open_objects.filter(
            side=BUY,
            symbol__enable=True,
            symbol__name='USDTIRT'
        ).aggregate(best_bid=Max('price'))['best_bid']

        tether_irt = get_external_price(coin=Asset.USDT, base_coin=Asset.IRT, side=SELL, allow_stale=allow_stale)

        prices[Asset.IRT] = Decimal(1) / get_external_price(
            coin=Asset.USDT, base_coin=Asset.IRT, side=BUY, allow_stale=allow_stale)

        return prices, market_prices, tether_irt


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('symbol', )


class AssetSerializerMini(serializers.ModelSerializer):
    precision = serializers.SerializerMethodField()
    step_size = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    original_name_fa = serializers.SerializerMethodField()
    original_symbol = serializers.SerializerMethodField()

    def get_precision(self, asset: Asset):
        return asset.get_precision()

    def get_step_size(self, asset: Asset):
        return Asset.PRECISION

    def get_logo(self, asset: Asset):
        return settings.MINIO_STORAGE_STATIC_URL + '/coins/%s.png' % asset.symbol

    def get_original_symbol(self, asset: Asset):
        return asset.get_original_symbol()

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
