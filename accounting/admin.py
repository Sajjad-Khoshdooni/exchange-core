from django.contrib import admin
from django.db.models import Sum
from simple_history.admin import SimpleHistoryAdmin

from accounting.models import Account, AccountTransaction, TransactionAttachment, Vault, VaultItem, ReservedAsset, \
    AssetPrice, TradeRevenue, PeriodicFetcher, BlocklinkIncome, BlocklinkDustCost
from accounting.models.provider_income import ProviderIncome
from ledger.utils.precision import humanize_number


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'iban', 'get_balance')
    readonly_fields = ('get_balance', )

    @admin.display(description='موجودی')
    def get_balance(self, account: Account):
        return humanize_number(account.get_balance())


class TransactionAttachmentTabularInline(admin.TabularInline):
    fields = ('created', 'type', 'file')
    readonly_fields = ('created', )
    model = TransactionAttachment
    extra = 1


@admin.register(AccountTransaction)
class AccountTransactionAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'amount', 'reason')
    readonly_fields = ('created', )
    inlines = (TransactionAttachmentTabularInline, )


@admin.register(Vault)
class VaultAdmin(admin.ModelAdmin):
    list_display = ('name', 'market', 'type', 'get_usdt', 'get_value', 'real_value')
    ordering = ('-real_value', )

    @admin.display(description='usdt')
    def get_usdt(self, vault: Vault):
        item = VaultItem.objects.filter(vault=vault, coin='USDT').first()

        if not item:
            return 0
        else:
            return item.balance

    @admin.display(description='value')
    def get_value(self, vault: Vault):
        return VaultItem.objects.filter(vault=vault).aggregate(sum=Sum('value_usdt'))['sum'] or 0


@admin.register(VaultItem)
class VaultItemAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('coin', 'vault', 'balance', 'value_usdt', 'value_irt', 'updated')
    search_fields = ('coin', )
    list_filter = ('vault__name', 'vault__type', 'vault__market')
    ordering = ('-value_usdt', )
    readonly_fields = ('value_usdt', 'value_irt')

    def save_model(self, request, obj, form, change):
        super(VaultItemAdmin, self).save_model(request, obj, form, change)
        obj.vault.update_real_value()


@admin.register(ReservedAsset)
class ReservedAssetAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('coin', 'amount', 'updated', 'value_usdt', 'value_irt')
    search_fields = ('coin', )


@admin.register(AssetPrice)
class AssetPriceAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ('coin', 'price', 'updated')
    search_fields = ('coin', )


@admin.register(TradeRevenue)
class TradeRevenueAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = (
        'created', 'symbol', 'source', 'side', 'amount', 'price', 'gap_revenue', 'fee_revenue', 'get_hedge_revenue',
        'coin_price', 'coin_filled_price', 'hedge_key', 'fiat_hedge_usdt', 'fiat_hedge_base')

    search_fields = ('group_id', 'hedge_key', 'symbol__name', )
    list_filter = ('symbol', 'source',)
    readonly_fields = ('account', 'symbol', 'group_id')

    @admin.display(description='hedge revenue')
    def get_hedge_revenue(self, revenue: TradeRevenue):
        return round(revenue.fiat_hedge_base * revenue.base_usdt_price + revenue.fiat_hedge_usdt, 3)


@admin.register(ProviderIncome)
class BinanceIncomeAdmin(admin.ModelAdmin):
    list_display = ('income_date', 'income_type', 'income', 'coin', 'symbol')
    search_fields = ('symbol', 'coin')
    list_filter = ('income_type', )
    ordering = ('-income_date', 'income_type')


@admin.register(PeriodicFetcher)
class PeriodicFetcherAdmin(admin.ModelAdmin):
    list_display = ('name', 'end')


@admin.register(BlocklinkIncome)
class BlocklinkIncomeAdmin(admin.ModelAdmin):
    list_display = ('start', 'network', 'real_fee_amount', 'fee_cost', 'fee_income',)
    list_filter = ('network', )


@admin.register(BlocklinkDustCost)
class BlocklinkDustCostAdmin(admin.ModelAdmin):
    list_display = ('updated', 'network', 'amount', 'usdt_value',)
