from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, FiatTransaction, \
    FiatWithdrawRequest
from financial.tasks import verify_bank_card_task, verify_bank_account_task
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
class BankCardAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    list_display = ('created', 'card_pan', 'user', 'verified')
    list_filter = (BankCardUserFilter,)

    fields_edit_conditions = {
        'verified': ~M('verified')
    }

    actions = ['verify_bank_cards']

    @admin.action(description='تایید خودکار شماره کارت')
    def verify_bank_cards(self, request, queryset):
        for bank_card in queryset.filter(verified__isnull=True):
            verify_bank_card_task.delay(bank_card.id)


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
class BankAccountAdmin(AdvancedAdmin):
    default_edit_condition = M.superuser

    list_display = ('created', 'iban', 'user', 'verified')
    list_filter = (BankUserFilter, )

    fields_edit_conditions = {
        'verified': ~M('verified')
    }

    actions = ['verify_bank_accounts']

    @admin.action(description='تایید خودکار شماره شبا')
    def verify_bank_accounts(self, request, queryset):
        for bank_account in queryset.filter(verified__isnull=True):
            verify_bank_account_task.delay(bank_account.id)

