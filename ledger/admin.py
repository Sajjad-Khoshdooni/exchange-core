from django.contrib import admin
from ledger import models


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'name_fa')


@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'name_fa', 'can_withdraw')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'commission', 'min_transfer')


@admin.register(models.NetworkWallet)
class NetworkWalletAdmin(admin.ModelAdmin):
    list_display = ('network', 'wallet', 'address', 'address_tag')


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'token', 'account', 'coin', 'side', 'price')


@admin.register(models.OTCTrade)
class OTCTradeAdmin(admin.ModelAdmin):
    list_display = ('created', 'otc_request', 'amount', 'status', 'group_id')


@admin.register(models.Trx)
class TrxAdmin(admin.ModelAdmin):
    list_display = ('created', 'sender', 'receiver', 'amount', 'group_id')


@admin.register(models.Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'asset', 'get_balance')

    def get_balance(self, wallet: models.Wallet):
        return float(wallet.get_balance())

    get_balance.short_description = 'balance'
