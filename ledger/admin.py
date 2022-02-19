from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F

from accounts.models import Account
from ledger import models
from ledger.models import Asset
from ledger.utils.overview import AssetOverview
from provider.exchanges import BinanceFuturesHandler


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'symbol', 'order', 'enable', 'get_hedge_value', 'get_hedge_amount',
        'get_future_amount', 'get_binance_spot_amount', 'get_internal_balance', 'get_ledger_balance_users',

        'get_hedge_threshold', 'get_future_value',
        'get_ledger_balance_system', 'get_ledger_balance_out', 'trend',
    )
    list_filter = ('enable', 'trend')
    list_editable = ('enable', 'order', 'trend')
    search_fields = ('symbol', )

    def changelist_view(self, request, extra_context=None):
        self.overview = AssetOverview()
        context = {
            'binance_initial_margin': round(self.overview.total_initial_margin, 2),
            'binance_maint_margin': round(self.overview.total_maintenance_margin, 2),
            'binance_margin_balance': round(self.overview.total_margin_balance, 2),
            'binance_margin_ratio': round(self.overview.margin_ratio, 2),
            'hedge_value': round(self.overview.get_total_hedge_value(), 2),
            'spot_usdt': round(self.overview.get_binance_spot_amount(Asset.get(Asset.USDT)), 2),
        }

        return super().changelist_view(request, extra_context=context)

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)

    def get_ledger_balance_users(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_ledger_balance(Account.ORDINARY, asset))

    get_ledger_balance_users.short_description = 'users'

    def get_ledger_balance_system(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_ledger_balance(Account.SYSTEM, asset))

    get_ledger_balance_system.short_description = 'system'

    def get_ledger_balance_out(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_ledger_balance(Account.OUT, asset))

    get_ledger_balance_out.short_description = 'out'

    def get_future_amount(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_future_position_amount(asset))

    get_future_amount.short_description = 'future amount'

    def get_future_value(self, asset: Asset):
        return round(self.overview.get_future_position_value(asset), 2)

    get_future_value.short_description = 'future usdt'

    def get_binance_spot_amount(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_binance_spot_amount(asset))

    get_binance_spot_amount.short_description = 'bin spot amount'

    def get_internal_balance(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_internal_deposits_balance(asset))

    get_internal_balance.short_description = 'internal'

    def get_hedge_amount(self, asset: Asset):
        return asset.get_presentation_amount(self.overview.get_hedge_amount(asset))

    get_hedge_amount.short_description = 'hedge amount'

    def get_hedge_value(self, asset: Asset):
        return round(self.overview.get_hedge_value(asset), 2)

    get_hedge_value.short_description = 'hedge value'

    def get_hedge_threshold(self, asset: Asset):
        return BinanceFuturesHandler.get_step_size(asset.symbol + 'USDT')

    get_hedge_threshold.short_description = 'future hedge threshold'



@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit', 'min_confirm', 'unlock_confirm', 'address_regex')
    list_editable = ('can_withdraw', 'can_deposit')
    search_fields = ('symbol', )
    list_filter = ('can_withdraw', 'can_deposit')
    ordering = ('-can_withdraw', '-can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_fee', 'withdraw_min', 'withdraw_max')
    search_fields = ('network__symbol', 'asset__symbol')


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
    list_display = ('created', 'network', 'wallet', 'amount', 'fee_amount', 'deposit', 'status', 'is_fee', 'source')
    search_fields = ('trx_hash', 'block_hash', 'block_number', 'out_address')
    list_filter = ('deposit', 'status', 'is_fee', 'source', 'status')


@admin.register(models.BalanceLock)
class BalanceLockAdmin(admin.ModelAdmin):
    list_display = ('created', 'release_date', 'wallet', 'amount', 'freed')
    list_filter = ('freed', 'wallet')
    ordering = ('-created', )


class CryptoAccountTypeFilter(SimpleListFilter):
    title = 'type' # or use _('country') for translated title
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return (Account.SYSTEM, 'system'), (Account.OUT, 'out'), ('ord', 'ordinary')

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            if value == 'ord':
                value = None

            return queryset.filter(deposit_address__account_secret__account__type=value)
        else:
            return queryset


@admin.register(models.CryptoBalance)
class CryptoBalanceAdmin(admin.ModelAdmin):
    list_display = ('asset', 'get_network', 'get_address', 'get_owner', 'amount', 'updated_at', )
    search_fields = ('asset__symbol', 'deposit_address__address',)
    list_filter = (CryptoAccountTypeFilter, )

    def get_network(self, crypto_balance: models.CryptoBalance):
        return crypto_balance.deposit_address.network

    get_network.short_description = 'network'

    def get_address(self, crypto_balance: models.CryptoBalance):
        return crypto_balance.deposit_address.presentation_address

    get_address.short_description = 'address'

    def get_owner(self, crypto_balance: models.CryptoBalance):
        return str(crypto_balance.deposit_address.account_secret.account)

    get_owner.short_description = 'owner'
