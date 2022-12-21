from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Sum
from django.utils import timezone
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.models import User
from accounts.utils.admin import url_to_edit_object
from accounts.utils.validation import gregorian_to_jalali_date_str
from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, FiatTransaction, \
    FiatWithdrawRequest, ManualTransferHistory, MarketingSource, MarketingCost, Investment, InvestmentRevenue, \
    FiatHedgeTrx
from financial.tasks import verify_bank_card_task, verify_bank_account_task
from financial.utils.withdraw import FiatWithdraw
from ledger.utils.precision import humanize_number, get_presentation_amount
from ledger.utils.price import get_tether_irt_price, BUY, SELL


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'merchant_id', 'active', 'active_for_staff', 'get_total_wallet_irt_value',
                    'min_deposit_amount', 'max_deposit_amount')
    list_editable = ('active', 'active_for_staff', 'min_deposit_amount', 'max_deposit_amount')
    readonly_fields = ('get_total_wallet_irt_value',)

    def get_total_wallet_irt_value(self, gateway: Gateway):
        if not gateway.type:
            return

        channel = FiatWithdraw.get_withdraw_channel(gateway.type)

        try:
            return humanize_number(Decimal(channel.get_total_wallet_irt_value()))
        except:
            return

    get_total_wallet_irt_value.short_description = 'موجودی'


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
        ('اطلاعات درخواست', {'fields': ('created', 'status', 'amount', 'fee_amount', 'ref_id', 'bank_account',
         'ref_doc', 'get_withdraw_request_receive_time', 'provider_withdraw_id')}),
        ('اطلاعات کاربر', {'fields': ('get_withdraw_request_iban', 'get_withdraw_request_user',
                                      'get_user')}),
        ('نظر', {'fields': ('comment',)})
    )
    list_filter = ('status', UserRialWithdrawRequestFilter, )
    ordering = ('-created', )
    readonly_fields = (
        'created', 'bank_account', 'amount', 'get_withdraw_request_iban', 'fee_amount',
        'get_withdraw_request_user', 'withdraw_channel', 'get_withdraw_request_receive_time', 'get_user'
    )

    list_display = ('bank_account', 'created', 'get_user', 'status', 'amount', 'withdraw_channel', 'ref_id')

    actions = ('resend_withdraw_request', )

    @admin.display(description='نام و نام خانوادگی')
    def get_withdraw_request_user(self, withdraw_request: FiatWithdrawRequest):
        return withdraw_request.bank_account.user.get_full_name()

    @admin.display(description='کاربر')
    def get_user(self, withdraw_request: FiatWithdrawRequest):
        link = url_to_edit_object(withdraw_request.bank_account.user)
        return mark_safe("<a href='%s'>%s</a>" % (link, withdraw_request.bank_account.user.phone))

    @admin.display(description='شماره شبا')
    def get_withdraw_request_iban(self, withdraw_request: FiatWithdrawRequest):
        return withdraw_request.bank_account.iban

    def get_withdraw_request_receive_time(self, withdraw: FiatWithdrawRequest):
        if withdraw.receive_datetime:
            return ('زمان : %s تاریخ %s' % (
                withdraw.receive_datetime.time().strftime("%H:%M"),
                gregorian_to_jalali_date_str(withdraw.receive_datetime.date())
            ))

    get_withdraw_request_receive_time.short_description = 'زمان تقریبی واریز'

    @admin.action(description='ارسال مجدد درخواست', permissions=['view'])
    def resend_withdraw_request(self, request, queryset):
        valid_qs = queryset.filter(
            status=FiatWithdrawRequest.PROCESSING,
            created__lt=timezone.now() - timedelta(seconds=FiatWithdrawRequest.FREEZE_TIME)
        )

        for fiat_withdraw in valid_qs:
            fiat_withdraw.create_withdraw_request()

    def save_model(self, request, obj: FiatWithdrawRequest, form, change):
        if obj.id:
            old = FiatWithdrawRequest.objects.get(id=obj.id)
            if old.status != obj.status:
                obj.change_status(obj.status)

        obj.save()


class PaymentRequestUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(bank_card__user_id=user)
        else:
            return queryset


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'gateway', 'bank_card', 'amount', 'authority')
    search_fields = ('bank_card__card_pan', 'amount', 'authority')
    readonly_fields = ('bank_card', )
    list_filter = (PaymentRequestUserFilter,)


class PaymentUserFilter(SimpleListFilter):
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
    list_display = ('created', 'get_payment_amount', 'status', 'ref_id', 'ref_status', 'get_user',)
    readonly_fields = ('payment_request', )
    list_filter = (PaymentUserFilter, 'status', )
    search_fields = ('ref_id', 'payment_request__bank_card__card_pan', 'payment_request__amount',
                     'payment_request__authority')

    @admin.display(description='مقدار')
    def get_payment_amount(self, payment: Payment):
        return humanize_number(payment.payment_request.amount)

    @admin.display(description='کاربر')
    def get_user(self, payment: Payment):
        link = url_to_edit_object(payment.payment_request.bank_card.user)
        return mark_safe("<a href='%s'>%s</a>" % (link, payment.payment_request.bank_card.user.phone))

    get_user.short_description = 'کاربر'


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
    readonly_fields = ('user', )

    actions = ['verify_bank_cards', 'verify_bank_cards_manual', 'reject_bank_cards_manual']

    fields_edit_conditions = {
        'verified': M.superuser | M('verified')
    }

    @admin.action(description='تایید خودکار شماره کارت')
    def verify_bank_cards(self, request, queryset):
        for bank_card in queryset.filter(kyc=False):
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
    readonly_fields = ('user', )

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


@admin.register(ManualTransferHistory)
class ManualTransferHistoryAdmin(SimpleHistoryAdmin):
    list_display = ('created', 'asset', 'amount', 'full_fill_amount', 'deposit', 'done')
    list_filter = ('deposit', 'done')


@admin.register(MarketingSource)
class MarketingSourceAdmin(admin.ModelAdmin):
    list_display = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')
    list_filter = ('utm_source', )


@admin.register(MarketingCost)
class MarketingCostAdmin(admin.ModelAdmin):
    list_display = ('source', 'date', 'cost')
    search_fields = ('source__utm_source', )


@admin.register(FiatHedgeTrx)
class FiatHedgeTrxAdmin(admin.ModelAdmin):
    list_display = ('base_amount', 'target_amount', 'price', 'get_side', 'source', 'reason')
    list_filter = ('source', )

    @admin.display(description='side')
    def get_side(self, fiat_hedge: FiatHedgeTrx):
        return BUY if fiat_hedge.target_amount > 0 else SELL

    def changelist_view(self, request, extra_context=None):

        aggregates = FiatHedgeTrx.objects.aggregate(
            total_base_amount=Sum('base_amount'),
            total_target_amount=Sum('target_amount'),
        )

        total_base = aggregates['total_base_amount'] or 0
        total_target = aggregates['total_target_amount'] or 0

        usdt_irt = get_tether_irt_price(BUY)

        context = {
            'irt': round(total_base),
            'usdt': round(total_target, 2),
            'total_value': round(total_target + total_base / usdt_irt, 2),
        }

        return super().changelist_view(request, extra_context=context)


class InvestmentRevenueInline(admin.TabularInline):
    fields = ('created', 'amount', 'description', 'revenue')
    readonly_fields = ('created', )
    model = InvestmentRevenue
    extra = 1


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('created', 'title', 'asset', 'get_total', 'get_amount', 'get_revenue', 'type')
    inlines = [InvestmentRevenueInline]
    list_filter = ('type', 'asset', )

    @admin.display(description='amount', ordering='amount')
    def get_amount(self, investment: Investment):
        return humanize_number(get_presentation_amount(investment.get_base_amount()))

    @admin.display(description='revenue')
    def get_revenue(self, investment: Investment):
        return humanize_number(get_presentation_amount(investment.get_revenue_amount()))

    @admin.display(description='total')
    def get_total(self, investment: Investment):
        return humanize_number(get_presentation_amount(investment.get_total_amount()))
