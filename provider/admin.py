from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum

from ledger.utils.overview import AssetOverview
from ledger.utils.price import get_price,BUY
from provider import models
from provider.models import BinanceWallet


@admin.register(models.ProviderOrder)
class ProviderOrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'side', 'market', 'amount', 'order_id', 'scope', 'hedge_amount', )
    search_fields = ('asset__symbol', 'order_id')
    list_filter = ('scope', )


@admin.register(models.ProviderTransfer)
class ProviderTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'network', 'amount', 'address', 'provider_transfer_id', 'caller_id')
    search_fields = ('asset__symbol', 'caller_id')


@admin.register(models.ProviderHedgedOrder)
class ProviderHedgedOrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'side', 'amount', 'caller_id', 'hedged')
    search_fields = ('asset__symbol', 'caller_id')


@admin.register(models.BinanceRequests)
class BinanceRequestsAdmin(admin.ModelAdmin):
    list_display = ('created', 'method', 'url', 'data', 'status_code')
    search_fields = ('url', 'status_code')
    list_filter = ('status_code', 'method',)


@admin.register(models.BinanceTransferHistory)
class BinanceTransferHistoryAdmin(admin.ModelAdmin):
    list_display = ['type', 'amount', 'coin', 'status', 'date', 'address', 'tx_id']
    list_filter = ['status', 'type']
    search_fields = ['address', 'coin']


@admin.register(BinanceWallet)
class BinanceWalletAdmin(admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):

        spot_wallets = BinanceWallet.objects.filter(type=BinanceWallet.SPOT).filter(free__gt=0)
        futures_wallets = BinanceWallet.objects.filter(type=BinanceWallet.FUTURES).filter(free__gt=0)

        spot_wallets_usdt_value = 0
        futures_wallet_usdt_value = 0

        for spot_wallet in spot_wallets:
            price = get_price(spot_wallet.asset, side=BUY)
            if price:
                spot_wallets_usdt_value += price * spot_wallet.free

        for futures_wallet in futures_wallets:
            price = get_price(futures_wallet.asset, side=BUY)
            if price:
                futures_wallet_usdt_value += price * futures_wallet.free

        context = {
            'spot_wallet': spot_wallets_usdt_value,
            'futures_wallet': futures_wallet_usdt_value,
        }
        return super().changelist_view(request, extra_context=context)

    list_display = ['asset', 'free', 'locked', 'get_usdt_value', 'type']
    search_fields = ['asset']
    readonly_fields = ('get_usdt_value','asset', 'free', 'locked', 'get_usdt_value', 'type')

    def get_usdt_value(self, binance_wallet: models.BinanceWallet):
        return get_price(coin=binance_wallet.asset, side=BUY) * binance_wallet.free
    get_usdt_value.short_description = 'USDT_Value'
