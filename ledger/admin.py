from django.contrib import admin
from django.db.models import F

from ledger import models
from ledger.models import Asset


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'order', 'enable', 'trade_quantity_step', 'min_trade_quantity', 'max_trade_quantity')
    list_filter = ('enable', )
    list_editable = ('enable', 'order')
    search_fields = ('symbol', )

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)



@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit')
    list_editable = ('can_withdraw', 'can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_commission', 'min_withdraw')


@admin.register(models.DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('account_secret', 'address')


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'from_asset', 'to_asset', 'to_price', 'from_amount', 'to_amount', 'token')

    def get_from_amount(self, otc_request: models.OTCRequest):
        return otc_request.from_asset.get_presentation_amount(otc_request.from_amount)

    get_from_amount.short_description = 'from_amount'

    def get_to_amount(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_amount)

    get_to_amount.short_description = 'to_amount'

    def get_to_price(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_price)

    get_to_price.short_description = 'to_price'


@admin.register(models.OTCTrade)
class OTCTradeAdmin(admin.ModelAdmin):
    list_display = ('created', 'otc_request',  'status', 'group_id')


@admin.register(models.Trx)
class TrxAdmin(admin.ModelAdmin):
    list_display = ('created', 'sender', 'receiver', 'amount', 'group_id')


@admin.register(models.Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'asset', 'get_free', 'get_locked')
    list_filter = ('account', 'asset')

    def get_free(self, wallet: models.Wallet):
        return float(wallet.get_free())

    get_free.short_description = 'free'

    def get_locked(self, wallet: models.Wallet):
        return float(wallet.get_locked())

    get_locked.short_description = 'locked'


@admin.register(models.Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'amount', 'deposit', 'status', 'trx_hash', )


@admin.register(models.BalanceLock)
class BalanceLockAdmin(admin.ModelAdmin):
    list_display = ('created', 'release_date', 'wallet', 'amount', 'freed')
    list_filter = ('freed', 'wallet')
    ordering = ('-created', )
