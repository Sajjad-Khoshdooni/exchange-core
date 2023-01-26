from django.contrib import admin

from accounting.models import Account, AccountTransaction, TransactionAttachment, Vault, VaultItem
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
    list_display = ('name', 'type')


@admin.register(VaultItem)
class VaultItemAdmin(admin.ModelAdmin):
    list_display = ('coin', 'vault', 'balance', 'value_usdt', 'value_irt', 'updated')
