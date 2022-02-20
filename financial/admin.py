from django.contrib import admin

from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, FiatTransaction, \
    FiatWithdrawRequest


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'merchant_id', 'active')
    list_editable = ('active', )


@admin.register(FiatTransaction)
class FiatTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'deposit', 'status', 'amount')
    list_filter = ('deposit', 'status')
    ordering = ('-created', )


@admin.register(FiatWithdrawRequest)
class FiatWithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'bank_account', 'status', 'amount', 'fee_amount')
    list_filter = ('status', )
    ordering = ('-created', )
    readonly_fields = ('amount', 'fee_amount', 'bank_account')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'gateway', 'bank_card', 'amount', 'authority')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('created', 'status', 'ref_id', 'ref_status', )


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ('created', 'card_pan', 'user', 'verified')


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('created', 'iban', 'user', 'verified')
