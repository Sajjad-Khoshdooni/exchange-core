from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, FiatTransaction, \
    FiatWithdrawRequest
from ledger.utils.precision import humanize_number


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'merchant_id', 'active')
    list_editable = ('active', )


@admin.register(FiatTransaction)
class FiatTransferRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'account', 'deposit', 'status', 'amount')
    list_filter = ('deposit', 'status')
    ordering = ('-created', )


class UserRialWithdrawRequestFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(bank_account__user_id=user)
        else:
            return queryset


@admin.register(FiatWithdrawRequest)
class FiatWithdrawRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'bank_account', 'status', 'amount', 'fee_amount')
    list_filter = ('status', UserRialWithdrawRequestFilter, )
    ordering = ('-created', )
    readonly_fields = ('amount', 'fee_amount', 'bank_account')


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'gateway', 'bank_card', 'amount', 'authority')


class UserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(payment_request__bank_card__user_id=user)
        else:
            return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('created', 'get_payment_amount', 'status', 'ref_id', 'ref_status', 'get_user_bank_card',)
    list_filter = (UserFilter,)

    def get_user_bank_card(self, payment: Payment):
        return payment.payment_request.bank_card.user

    get_user_bank_card.short_description = 'کاربر'
    
    def get_payment_amount(self, payment: Payment):
        return humanize_number(payment.payment_request.amount)
    
    get_payment_amount.short_description = 'مقدار'


class BankCardUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(user_id=user)
        else:
            return queryset


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ('created', 'card_pan', 'user', 'verified')
    list_filter = (BankCardUserFilter,)


class BankUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(user_id=user)
        else:
            return queryset


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('created', 'iban', 'user', 'verified')
    list_filter = (BankUserFilter, )


