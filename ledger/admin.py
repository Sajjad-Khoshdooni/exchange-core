from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from ledger.utils.precision import get_presentation_amount
from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.models import Account
from ledger import models
from ledger.models import Asset, Prize
from ledger.utils.overview import AssetOverview
from ledger.utils.price import get_trading_price_usdt, BUY
from provider.exchanges import BinanceFuturesHandler
from ledger.utils.precision import humanize_number
from provider.models import ProviderOrder


@admin.register(models.Asset)
class AssetAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'order': True,
        'trend': True,
        'bid_diff': True,
        'ask_diff': True
    }

    readonly_fields = ('get_calculated_hedge_amount', 'get_hedge_value', 'get_hedge_amount')

    list_display = (
        'symbol', 'order', 'enable', 'get_hedge_value', 'get_hedge_amount',
        'get_future_amount', 'get_binance_spot_amount', 'get_internal_balance',
        'get_ledger_balance_users', 'get_total_asset', 'get_hedge_threshold', 'get_future_value',
        'get_ledger_balance_system', 'get_ledger_balance_out', 'trend', 'trade_enable', 'hedge_method', 'bid_diff', 'ask_diff'
    )
    list_filter = ('enable', 'trend')
    list_editable = ('enable', 'order', 'trend', 'trade_enable')
    search_fields = ('symbol', )

    def changelist_view(self, request, extra_context=None):

        if not settings.DEBUG:
            self.overview = AssetOverview()
            context = {
                'binance_initial_margin': round(self.overview.total_initial_margin, 2),
                'binance_maint_margin': round(self.overview.total_maintenance_margin, 2),
                'binance_margin_balance': round(self.overview.total_margin_balance, 2),
                'binance_margin_ratio': round(self.overview.margin_ratio, 2),
                'hedge_value': round(self.overview.get_total_hedge_value(), 2),
                'binance_spot_usdt': round(self.overview.get_binance_spot_amount(Asset.get(Asset.USDT)), 2),
                'internal_usdt': round(self.overview.get_internal_usdt_value(), 2)
            }
        else:
            self.overview = None
            context = {}

        return super().changelist_view(request, extra_context=context)

    def save_model(self, request, obj, form, change):
        if Asset.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Asset.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(AssetAdmin, self).save_model(request, obj, form, change)

    def get_ledger_balance_users(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(
            self.overview.get_ledger_balance(Account.ORDINARY, asset)
        )

    get_ledger_balance_users.short_description = 'users'

    def get_ledger_balance_system(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_ledger_balance(Account.SYSTEM, asset))

    get_ledger_balance_system.short_description = 'system'

    def get_ledger_balance_out(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_ledger_balance(Account.OUT, asset))

    get_ledger_balance_out.short_description = 'out'

    def get_total_asset(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_total_assets(asset))

    get_total_asset.short_description = 'total assets'

    def get_future_amount(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_future_position_amount(asset))

    get_future_amount.short_description = 'future amount'

    def get_future_value(self, asset: Asset):
        return self.overview and round(self.overview.get_future_position_value(asset), 2)

    get_future_value.short_description = 'future usdt'

    def get_binance_spot_amount(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_binance_spot_amount(asset))

    get_binance_spot_amount.short_description = 'bin spot amount'

    def get_internal_balance(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_internal_deposits_balance(asset))

    get_internal_balance.short_description = 'internal'

    def get_hedge_amount(self, asset: Asset):
        return self.overview and asset.get_presentation_amount(self.overview.get_hedge_amount(asset))

    get_hedge_amount.short_description = 'hedge amount'

    def get_calculated_hedge_amount(self, asset: Asset):
        return asset.get_presentation_amount(ProviderOrder.get_hedge(asset))

    get_calculated_hedge_amount.short_description = 'calc hedge amount'

    def get_hedge_value(self, asset: Asset):
        hedge_value = self.overview and self.overview.get_hedge_value(asset)

        if hedge_value is not None:
            hedge_value = round(hedge_value, 2)

        return hedge_value

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
    list_display = ('network', 'asset', 'withdraw_fee', 'withdraw_min', 'withdraw_max', 'binance_withdraw_enable')
    search_fields = ('network__symbol', 'asset__symbol')


@admin.register(models.DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('account_secret', 'network', 'address')


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'from_asset', 'to_asset', 'to_price', 'from_amount', 'to_amount', 'token')

    def get_from_amount(self, otc_request: models.OTCRequest):
        return humanize_number((otc_request.from_asset.get_presentation_amount(otc_request.from_amount)))

    get_from_amount.short_description = 'from_amount'

    def get_to_amount(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_amount)

    get_to_amount.short_description = 'to_amount'

    def get_to_price(self, otc_request: models.OTCRequest):
        return otc_request.to_asset.get_presentation_amount(otc_request.to_price)

    get_to_price.short_description = 'to_price'


class OTCUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(otc_request__account__user_id=user)
        else:
            return queryset


@admin.register(models.OTCTrade)
class OTCTradeAdmin(admin.ModelAdmin):
    list_display = ('created', 'otc_request', 'status', 'get_otc_trade_to_price_absolute_irt', )
    list_filter = (OTCUserFilter, 'status')
    search_fields = ('group_id', )
    readonly_fields = ('otc_request', )

    def get_otc_trade_from_amount(self, otc_trade: models.OTCTrade):
        return humanize_number(
            otc_trade.otc_request.from_asset.get_presentation_amount(otc_trade.otc_request.from_amount)
        )

    get_otc_trade_from_amount.short_description = 'مقدار پایه'

    def get_otc_trade_to_price_absolute_irt(self, otc_trade: models.OTCTrade):
        return humanize_number(int(
            otc_trade.otc_request.to_price_absolute_irt * otc_trade.otc_request.to_amount
        ))
    get_otc_trade_to_price_absolute_irt.short_description = 'ارزش ریالی'


@admin.register(models.Trx)
class TrxAdmin(admin.ModelAdmin):
    list_display = ('created', 'sender', 'receiver', 'amount', 'group_id')
    search_fields = ('sender__asset__symbol', 'sender__account__user__phone', 'receiver__account__user__phone')


class WalletUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'account'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        account = request.GET.get('account')
        if account is not None:
            return queryset.filter(account=account)
        else:
            return queryset


@admin.register(models.Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'asset', 'market', 'get_free', 'get_locked', 'get_free_usdt', 'get_free_irt')
    list_filter = [
        ('asset', RelatedDropdownFilter),
        WalletUserFilter
    ]

    def get_free(self, wallet: models.Wallet):
        return float(wallet.get_free())

    get_free.short_description = 'free'

    def get_locked(self, wallet: models.Wallet):
        return float(wallet.get_locked())

    get_locked.short_description = 'locked'

    def get_free_irt(self, wallet: models.Wallet):
        return wallet.asset.get_presentation_price_irt(wallet.get_balance_irt())
    get_free_irt.short_description = 'ارزش ریالی'

    def get_free_usdt(self, wallet: models.Wallet):
        return wallet.asset.get_presentation_price_usdt(wallet.get_balance_usdt())
    get_free_usdt.short_description = 'ارزش دلاری'


class TransferUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(wallet__account__user_id=user)
        else:
            return queryset


@admin.register(models.Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'network', 'wallet', 'amount', 'fee_amount', 'deposit', 'status', 'is_fee', 'source')
    search_fields = ('trx_hash', 'block_hash', 'block_number', 'out_address', 'wallet__asset__symbol')
    list_filter = ('deposit', 'status', 'is_fee', 'source', 'status', TransferUserFilter,)
    readonly_fields = ('deposit_address', 'network', 'wallet', 'lock', 'provider_transfer')


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
    list_display = ('asset', 'get_network', 'get_address', 'get_owner', 'amount', 'get_value_usdt', 'updated_at', )
    search_fields = ('asset__symbol', 'deposit_address__address',)
    list_filter = (CryptoAccountTypeFilter, )
    actions = ('collect_asset_action', )

    def get_network(self, crypto_balance: models.CryptoBalance):
        return crypto_balance.deposit_address.network

    get_network.short_description = 'network'

    def get_address(self, crypto_balance: models.CryptoBalance):
        return crypto_balance.deposit_address.presentation_address

    get_address.short_description = 'address'

    def get_owner(self, crypto_balance: models.CryptoBalance):
        return str(crypto_balance.deposit_address.account_secret.account)

    get_owner.short_description = 'owner'

    def get_value_usdt(self, crypto_balance: models.CryptoBalance):
        value = crypto_balance.amount * get_trading_price_usdt(crypto_balance.asset.symbol, BUY, raw_price=True)
        return get_presentation_amount(value)

    get_value_usdt.short_description = 'value'

    @admin.action(description='ارسال به بایننس')
    def collect_asset_action(self, request, queryset):
        for crypto in queryset:
            crypto.collect()


@admin.register(models.MarginTransfer)
class MarginTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', )
    search_fields = ('group_id',)


@admin.register(models.MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', 'asset', 'status')
    search_fields = ('group_id',)


@admin.register(models.MarginLiquidation)
class MarginLiquidationAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'margin_level', 'group_id')
    search_fields = ('group_id',)


@admin.register(models.AddressBook)
class AddressBookAdmin(admin.ModelAdmin):
    list_display = ('name', 'account', 'network', 'address', 'asset',)
    search_fields = ('address', 'name')


@admin.register(models.Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('created', 'scope', 'account', 'get_asset_amount')

    def get_asset_amount(self, prize: Prize):
        return str(get_presentation_amount(prize.amount)) + str(prize.asset)

    get_asset_amount.short_description = 'مقدار'
