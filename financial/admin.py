from django.contrib import admin
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from datetime import timedelta

from simple_history.admin import SimpleHistoryAdmin

from accounts.models import User
from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.tasks.verify_user import alert_user_verify_status
from accounts.utils.admin import url_to_admin_list
from accounts.utils.validation import gregorian_to_jalali_date_str
from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, FiatTransaction, \
    FiatWithdrawRequest
from financial.tasks import verify_bank_card_task, verify_bank_account_task
from ledger.utils.precision import humanize_number
from financial.utils.withdraw_limit import get_fiat_estimate_receive_time

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
        ('اطلاعات درخواست', {'fields': ('created', 'status', 'amount', 'fee_amount', 'ref_id', 'ref_doc',
                                        'get_withdraw_request_receive_time', 'provider_withdraw_id')}),
        ('اطلاعات کاربر', {'fields': ('get_withdraw_request_iban', 'get_withdraw_request_user',
                                      'get_withdraw_request_user_mobile')}),
        ('نظر', {'fields': ('comment',)})
    )
    # list_display = ('bank_account', )
    list_filter = ('status', UserRialWithdrawRequestFilter, )
    ordering = ('-created', )
    readonly_fields = ('amount', 'fee_amount', 'bank_account', 'created', 'get_withdraw_request_iban',
                       'get_withdraw_request_user', 'get_withdraw_request_user_mobile', 'withdraw_channel',
                       'get_withdraw_request_receive_time'
                       )

    list_display = ('bank_account', 'created', 'status', 'amount', 'withdraw_channel', 'ref_id')

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

    def get_withdraw_request_receive_time(self, withdraw: FiatWithdrawRequest):
        if withdraw.withdraw_datetime:
            data_time = get_fiat_estimate_receive_time(withdraw.withdraw_datetime)

            return ('زمان : %s تاریخ %s' % (
                data_time.time().strftime("%H:%M"),
                gregorian_to_jalali_date_str(data_time.date())
            ))

    get_withdraw_request_receive_time.short_description = 'زمان تقریبی واریز'


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
class BankCardAdmin(SimpleHistoryAdmin, AdvancedAdmin):
    default_edit_condition = M.superuser

    list_display = ('created', 'card_pan', 'user', 'verified', 'deleted')
    list_filter = (BankCardUserFilter,)
    search_fields = ('card_pan', )

    actions = ['verify_bank_cards', 'verify_bank_cards_manual', 'reject_bank_cards_manual']

    fields_edit_conditions = {
        'verified': M.superuser | M('verified')
    }

    @admin.action(description='تایید خودکار شماره کارت')
    def verify_bank_cards(self, request, queryset):
        for bank_card in queryset:
            verify_bank_card_task.delay(bank_card.id)

    @admin.action(description='تایید شماره کارت')
    def verify_bank_cards_manual(self, request, queryset):
        for card in queryset:
            card.verified = True
            card.save()
            card.user.verify_level2_if_not()

    @admin.action(description='رد شماره کارت')
    def reject_bank_cards_manual(self, request, queryset):
        for card in queryset:
            card.verified = False
            card.save()

            user = card.user

            if user.level == User.LEVEL1 and user.verify_status == User.PENDING:
                user.change_status(User.REJECTED)


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
class BankAccountAdmin(SimpleHistoryAdmin, AdvancedAdmin):
    default_edit_condition = M.superuser

    list_display = ('created', 'iban', 'user', 'verified', 'deleted')
    list_filter = (BankUserFilter, )
    search_fields = ('iban', )

    actions = ['verify_bank_accounts_manual', 'verify_bank_accounts_auto', 'reject_bank_accounts_manual']

    fields_edit_conditions = {
        'verified': M.superuser | M('verified')
    }

    @admin.action(description='درخواست تایید خودکار شماره شبا')
    def verify_bank_accounts_auto(self, request, queryset):
        for bank_account in queryset:
            verify_bank_account_task.delay(bank_account.id)

    @admin.action(description='تایید شماره شبا')
    def verify_bank_accounts_manual(self, request, queryset):
        for bank_account in queryset:
            bank_account.verified = True
            bank_account.save()
            bank_account.user.verify_level2_if_not()

    @admin.action(description='رد شماره شبا')
    def reject_bank_accounts_manual(self, request, queryset):
        for bank_account in queryset:
            bank_account.verified = False
            bank_account.save()

            user = bank_account.user

            if user.level == User.LEVEL1 and user.verify_status == User.PENDING:
                user.change_status(User.REJECTED)
