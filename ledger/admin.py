from django.contrib import admin
from django.db.models import F

from accounts.models import Account
from ledger import models
from ledger.models import Asset
from ledger.utils.overview import get_user_type_balance
from provider.exchanges import BinanceFuturesHandler


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'symbol', 'order', 'enable', 'get_future_amount', 'get_future_value',
        'get_ledger_balance_users', 'get_ledger_balance_system', 'get_ledger_balance_out',
    )
    list_filter = ('enable', )
    list_editable = ('enable', 'order')
    search_fields = ('symbol', )

    def changelist_view(self, request, extra_context=None):
        detail = BinanceFuturesHandler.get_account_details()

        self.future_positions = {
            pos['symbol']: pos for pos in detail['positions']
        }

        context = {
            'binance_initial_margin': round(float(detail['totalInitialMargin']), 2),
            'binance_maint_margin': round(float(detail['totalMaintMargin']), 2),
            'binance_margin_balance': round(float(detail['totalMarginBalance']), 2),
            'binance_margin_ratio': round(float(detail['totalMarginBalance']) / float(detail['totalMaintMargin']), 2),
        }

        return super().changelist_view(request, extra_context=context)

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)

    def get_ledger_balance_users(self, asset: Asset):
        return get_user_type_balance(Account.ORDINARY, asset)

    get_ledger_balance_users.short_description = 'users'

    def get_ledger_balance_system(self, asset: Asset):
        return get_user_type_balance(Account.SYSTEM, asset)

    get_ledger_balance_system.short_description = 'system'

    def get_ledger_balance_out(self, asset: Asset):
        return get_user_type_balance(Account.OUT, asset)

    get_ledger_balance_out.short_description = 'out'

    def get_future_amount(self, asset: Asset):
        return self.future_positions.get(asset.symbol + 'USDT', {}).get('positionAmt', 0)

    get_future_amount.short_description = 'future amount'

    def get_future_value(self, asset: Asset):
        return round(float(self.future_positions.get(asset.symbol + 'USDT', {}).get('notional', 0)), 2)

    get_future_value.short_description = 'future usdt'


@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit')
    list_editable = ('can_withdraw', 'can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_commission', 'min_withdraw')


@admin.register(models.DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('account_secret', 'network', 'address')


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
