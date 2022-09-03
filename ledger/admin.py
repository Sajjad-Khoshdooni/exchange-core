from django.conf import settings
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.models import Account
from ledger import models
from ledger.models import Asset, Prize, CoinCategory, FastBuyToken
from ledger.utils.overview import AssetOverview
from ledger.utils.precision import get_presentation_amount
from ledger.utils.precision import humanize_number
from ledger.utils.price import get_trading_price_usdt, SELL
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
        'symbol', 'enable', 'get_hedge_value', 'get_hedge_amount', 'get_calculated_hedge_amount',
        'get_total_asset', 'get_ledger_balance_users',

        'get_future_amount', 'get_binance_spot_amount', 'get_internal_balance',
        'order', 'trend', 'trade_enable', 'hedge_method',

        'candidate', 'margin_enable', 'new_coin', 'spread_category'
    )
    list_filter = ('enable', 'trend', 'candidate', 'margin_enable', 'spread_category')
    list_editable = ('enable', 'order', 'trend', 'trade_enable', 'candidate', 'margin_enable', 'new_coin')
    search_fields = ('symbol', )
    ordering = ('-enable', '-pin_to_top', '-trend', 'order')
    actions = ('hedge_asset', )

    def changelist_view(self, request, extra_context=None):

        if not settings.DEBUG_OR_TESTING_OR_STAGING:
            self.overview = AssetOverview(strict=False)

            context = {
                'binance_initial_margin': round(self.overview.total_initial_margin, 2),
                'binance_maint_margin': round(self.overview.total_maintenance_margin, 2),
                'binance_margin_ratio': round(self.overview.margin_ratio, 2),
                'hedge_value': round(self.overview.get_total_hedge_value(), 2),
                'binance_spot_tether_amount': round(self.overview.get_binance_spot_amount(Asset.get(Asset.USDT)), 2),
                'kucoin_spot_tether_amount': round(self.overview.get_kucoin_spot_amount(Asset.get(Asset.USDT)), 2),
                'mexc_spot_tether_amount': round(self.overview.get_mexc_spot_amount(Asset.get(Asset.USDT)), 2),

                'binance_spot_usdt': round(self.overview.get_binance_spot_total_value(), 2),
                'kucoin_spot_usdt': round(self.overview.get_kucoin_spot_total_value(), 2),
                'mexc_spot_usdt': round(self.overview.get_mexc_spot_total_value(), 2),

                'binance_margin_balance': round(self.overview.total_margin_balance, 2),
                'internal_usdt': round(self.overview.get_internal_usdt_value(), 2),
                'fiat_usdt': round(self.overview.get_gateway_usdt(), 0),
                'margin_insurance_balance': self.overview.get_margin_insurance_balance(),
                'investment': round(self.overview.get_total_investment(), 0),
                'cash': round(self.overview.get_total_cash(), 0),

                'total_assets_usdt': round(self.overview.get_all_assets_usdt(), 0),
                'exchange_assets_usdt': round(self.overview.get_exchange_assets_usdt(), 0),
                'exchange_potential_usdt': round(self.overview.get_exchange_potential_usdt(), 0),
                'users_usdt': round(self.overview.get_all_users_asset_value(), 0)
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
            self.overview.get_users_asset_amount(asset)
        )

    get_ledger_balance_users.short_description = 'users'

    def get_users_usdt_value(self, asset: Asset):
        return self.overview and round(self.overview.get_users_asset_value(asset), 2)

    get_users_usdt_value.short_description = 'usdt_value'

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
        if asset.enable:
            handler = asset.get_hedger()

            if handler:
                symbol = handler.get_trading_symbol(asset.symbol)
                return handler.get_step_size(symbol)

    get_hedge_threshold.short_description = 'hedge threshold'

    @admin.action(description='متعادل سازی رمز ارزها', permissions=['view'])
    def hedge_asset(self, request, queryset):
        assets = queryset.exclude(hedge_method=Asset.HEDGE_NONE, )
        for asset in assets:
            ProviderOrder.try_hedge_for_new_order(asset, ProviderOrder.HEDGE)


@admin.register(models.Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'can_withdraw', 'can_deposit', 'min_confirm', 'unlock_confirm', 'address_regex')
    list_editable = ('can_withdraw', 'can_deposit')
    search_fields = ('symbol', )
    list_filter = ('can_withdraw', 'can_deposit')
    ordering = ('-can_withdraw', '-can_deposit')


@admin.register(models.NetworkAsset)
class NetworkAssetAdmin(admin.ModelAdmin):
    list_display = ('network', 'asset', 'withdraw_fee', 'withdraw_min', 'withdraw_max', 'can_deposit', 'can_withdraw',
                    'hedger_withdraw_enable')
    search_fields = ('asset__symbol', )
    list_editable = ('can_deposit', 'can_withdraw', )
    list_filter = ('network', )


class DepositAddressUserFilter(admin.SimpleListFilter):
    title = 'کاربران'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(address_key__account__user=user)
        else:
            return queryset


@admin.register(models.DepositAddress)
class DepositAddressAdmin(admin.ModelAdmin):
    list_display = ('address_key', 'network', 'address',)
    readonly_fields = ('address_key', 'network', 'address',)
    list_filter = ('network', DepositAddressUserFilter)
    search_fields = ('address',)


@admin.register(models.OTCRequest)
class OTCRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'from_asset', 'to_asset', 'to_price', 'from_amount', 'to_amount', 'token')
    readonly_fields = ('account', )

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
    list_display = ('created', 'sender', 'receiver', 'amount', 'scope', 'group_id', 'scope')
    search_fields = ('sender__asset__symbol', 'sender__account__user__phone', 'receiver__account__user__phone', 'group_id')
    readonly_fields = ('sender', 'receiver', )
    list_filter = ('scope', )


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
    readonly_fields = ('account', 'asset', 'market')

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
    list_display = ('created', 'network', 'wallet', 'amount', 'fee_amount',
                    'deposit', 'status', 'is_fee', 'source', 'get_total_volume_usdt',
                    )
    search_fields = ('trx_hash', 'block_hash', 'block_number', 'out_address', 'wallet__asset__symbol')
    list_filter = ('deposit', 'status', 'is_fee', 'source', 'status', TransferUserFilter,)
    readonly_fields = ('deposit_address', 'network', 'wallet', 'provider_transfer', 'get_total_volume_usdt')

    def get_total_volume_usdt(self, transfer: models.Transfer):
        price = get_trading_price_usdt(coin=transfer.wallet.asset.symbol, side=SELL)
        if price:
            return transfer.amount * price

    get_total_volume_usdt.short_description = 'ارزش تتری'


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

            return queryset.filter(deposit_address__address_key__account__type=value)
        else:
            return queryset


@admin.register(models.MarginTransfer)
class MarginTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', )
    search_fields = ('group_id',)


@admin.register(models.MarginLoan)
class MarginLoanAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'type', 'asset', 'status')
    search_fields = ('group_id',)


@admin.register(models.CloseRequest)
class MarginLiquidationAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'margin_level', 'group_id', 'status')
    search_fields = ('group_id',)
    list_filter = ('status', )


@admin.register(models.AddressBook)
class AddressBookAdmin(admin.ModelAdmin):
    list_display = ('name', 'account', 'network', 'address', 'asset',)
    search_fields = ('address', 'name')


@admin.register(models.Prize)
class PrizeAdmin(admin.ModelAdmin):
    list_display = ('created', 'scope', 'account', 'get_asset_amount')
    readonly_fields = ('account', 'asset', )

    def get_asset_amount(self, prize: Prize):
        return str(get_presentation_amount(prize.amount)) + str(prize.asset)

    get_asset_amount.short_description = 'مقدار'


@admin.register(models.CoinCategory)
class CoinCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_coin_count']

    def get_coin_count(self, coin_category: CoinCategory):
        return coin_category.coins.count()

    get_coin_count.short_description = 'تعداد رمزارز'


@admin.register(models.AddressKey)
class AddressKeyAdmin(admin.ModelAdmin):
    list_display = ('address', )
    readonly_fields = ('address', 'account')
    search_fields = ('address', 'public_address')
    list_filter = ('architecture', )


@admin.register(models.AssetSpreadCategory)
class AssetSpreadCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', )


@admin.register(models.PNLHistory)
class PNLHistoryAdmin(admin.ModelAdmin):
    list_display = ('date', 'account', 'market', 'base_asset', 'snapshot_balance', 'profit')
    readonly_fields = ('date', 'account', 'market', 'base_asset', 'snapshot_balance', 'profit')


@admin.register(models.CategorySpread)
class CategorySpreadAdmin(admin.ModelAdmin):
    list_display = ('category', 'step', 'side', 'spread')
    list_editable = ('side', 'step', 'spread')
    ordering = ('category', 'step', 'side')
    list_filter = ('category', 'side', 'step')


@admin.register(models.SystemSnapshot)
class SystemSnapshotAdmin(admin.ModelAdmin):
    list_display = ('created', 'total', 'users', 'exchange', 'exchange_potential', 'hedge', 'cumulated_hedge',
                    'binance_futures', 'binance_spot', 'kucoin_spot', 'mexc_spot', 'internal', 'fiat_gateway',
                    'investment', 'cash', 'prize', 'verified')
    ordering = ('-created', )
    actions = ('reject_histories', 'verify_histories')

    @admin.action(description='رد', permissions=['change'])
    def reject_histories(self, request, queryset):
        queryset.update(verified=False)

    @admin.action(description='تایید', permissions=['change'])
    def verify_histories(self, request, queryset):
        queryset.update(verified=True)


@admin.register(models.AssetSnapshot)
class AssetSnapshotAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'total_amount', 'users_amount', 'hedge_amount', 'hedge_value', 'get_hedge_diff')
    ordering = ('-created', 'asset__order')
    list_filter = ('asset', )

    def get_hedge_diff(self, asset_snapshot: models.AssetSnapshot):
        return asset_snapshot.calc_hedge_amount - asset_snapshot.hedge_amount

    get_hedge_diff.short_description = 'hedge diff'


@admin.register(models.FastBuyToken)
class FastBuyTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'asset', 'get_amount', 'status', 'created', ]
    readonly_fields = ('get_amount',)
    list_filter = ('status', )

    def get_amount(self, fast_buy_token: FastBuyToken):
        return get_presentation_amount(fast_buy_token.amount)
    get_amount.short_description = 'مقدار'
