from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe

from accounts.models import User
from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.utils.admin import url_to_admin_list
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
    raw_id_fields = ('account', )
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
    fieldsets = (
        ('اطلاعات درخواست', {'fields': ('created', 'status', 'amount', 'fee_amount', 'ref_id', 'ref_doc')}),
        ('اطلاعات کاربر', {'fields': ('get_withdraw_request_iban', 'get_withdraw_request_user',
                                      'get_withdraw_request_user_mobile')})
    )
    # list_display = ('bank_account', )
    list_filter = ('status', UserRialWithdrawRequestFilter, )
    ordering = ('-created', )
    readonly_fields = ('amount', 'fee_amount', 'bank_account', 'created', 'get_withdraw_request_iban',
                       'get_withdraw_request_user', 'get_withdraw_request_user_mobile',
                       )

    list_display = ('bank_account', 'status', 'amount', 'ref_id')

    def get_withdraw_request_user(self, withdraw_request: FiatWithdrawRequest):
        return withdraw_request.bank_account.user.get_full_name()
    get_withdraw_request_user.short_description = 'نام و نام خانوادگی'

    def get_withdraw_request_user_mobile(self, withdraw_request: FiatWithdrawRequest):
        link = url_to_admin_list(User) + '{}'.format(withdraw_request.bank_account.user.id) + '/change'
        return mark_safe("<a href='%s'>%s</a>" % (link, withdraw_request.bank_account.user.phone))
    get_withdraw_request_user_mobile.short_description = 'تلفن همراه'

    def get_withdraw_request_iban(self, withdraw_request: FiatWithdrawRequest):
        return withdraw_request.bank_account.iban
    get_withdraw_request_iban.short_description = 'شماره شبا'


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
    list_display = ('created', 'get_payment_amount', 'status', 'ref_id', 'ref_status', 'get_user_bank_card',
                    'get_withdraw_request_user_mobile',)
    list_filter = (UserFilter,)

    def get_user_bank_card(self, payment: Payment):
        return payment.payment_request.bank_card.user

    get_user_bank_card.short_description = 'کاربر'
    
    def get_payment_amount(self, payment: Payment):
        return humanize_number(payment.payment_request.amount)
    
    get_payment_amount.short_description = 'مقدار'

    def get_withdraw_request_user_mobile(self, payment: Payment):
        link = url_to_admin_list(User) + '{}'.format(payment.payment_request.bank_card.user.id) + '/change'
        return mark_safe("<a href='%s'>%s</a>" % (link, payment.payment_request.bank_card.user.phone))

    get_withdraw_request_user_mobile.short_description = 'کاربر'


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

    actions = ['verify_bank_cards']

    fields_edit_conditions = {
        'verified': M('verified')
    }

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

    actions = ['verify_bank_accounts_manual', 'verify_bank_accounts_auto']

    fields_edit_conditions = {
        'verified': M('verified')
    }

    @admin.action(description='درخواست تایید خودکار شماره شبا')
    def verify_bank_accounts_auto(self, request, queryset):
        for bank_account in queryset.filter(verified__isnull=True):
            verify_bank_account_task.delay(bank_account.id)

    @admin.action(description='تایید دستی شماره شبا')
    def verify_bank_accounts_manual(self, request, queryset):
        for bank_account in queryset.exclude(verified=True):
            bank_account.verified = True
            bank_account.save()
            bank_account.user.verify_level2_if_not()
