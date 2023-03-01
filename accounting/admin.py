from django.contrib import admin
from django.db.models import Sum
from simple_history.admin import SimpleHistoryAdmin

from accounting.models import Account, AccountTransaction, TransactionAttachment, Vault, VaultItem, ReservedAsset, \
    AssetPrice, TradeRevenue
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
        'created', 'symbol', 'source', 'side', 'amount', 'price', 'gap_revenue', 'fee_revenue',
        'coin_price', 'coin_filled_price', 'hedge_key', 'fiat_hedge_usdt', 'fiat_hedge_base', 'get_usdt_price')

    search_fields = ('group_id', 'hedge_key', 'symbol__name', )
    list_filter = ('symbol', 'source',)
    readonly_fields = ('account', 'symbol', 'group_id')

    @admin.display('usdt price')
    def get_usdt_price(self, revenue: TradeRevenue):
        if revenue.fiat_hedge_usdt:
            return -revenue.fiat_hedge_base / revenue.fiat_hedge_usdt
