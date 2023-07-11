from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, F
from django.utils import timezone
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from accounting.models import VaultItem, Vault
from accounts.admin_guard import M
from accounts.admin_guard.admin import AdvancedAdmin
from accounts.models import User
from accounts.models.user_feature_perm import UserFeaturePerm
from accounts.utils.admin import url_to_edit_object
from accounts.utils.validation import gregorian_to_jalali_date_str
from financial.models import Gateway, PaymentRequest, Payment, BankCard, BankAccount, \
    FiatWithdrawRequest, ManualTransfer, MarketingSource, MarketingCost, PaymentIdRequest, PaymentId, \
    GeneralBankAccount, BankPaymentRequest
from financial.tasks import verify_bank_card_task, verify_bank_account_task, process_withdraw
from financial.utils.payment_id_client import get_payment_id_client
from financial.utils.withdraw import FiatWithdraw
from ledger.utils.fields import PENDING
from ledger.utils.precision import humanize_number
from ledger.utils.withdraw_verify import RiskFactor


@admin.register(Gateway)
class GatewayAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'merchant_id', 'active', 'deposit_priority', 'active_for_staff', 'withdraw_enable',
                    'get_balance', 'get_min_deposit_amount', 'get_max_deposit_amount')
    list_editable = ('active', 'active_for_staff', 'withdraw_enable', 'deposit_priority')
    readonly_fields = ('get_balance', 'get_min_deposit_amount', 'get_max_deposit_amount')

    @admin.display(description='balance')
    def get_balance(self, gateway: Gateway):
        v = VaultItem.objects.filter(vault__type=Vault.GATEWAY, vault__key=gateway.id).first()
        return v and v.value_irt

    @admin.display(description='min deposit')
    def get_min_deposit_amount(self, gateway: Gateway):
        return humanize_number(Decimal(gateway.min_deposit_amount))

    @admin.display(description='max deposit')
    def get_max_deposit_amount(self, gateway: Gateway):
        return humanize_number(Decimal(gateway.max_deposit_amount))


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
class FiatWithdrawRequestAdmin(SimpleHistoryAdmin):

    fieldsets = (
        ('اطلاعات درخواست', {'fields': ('created', 'status', 'amount', 'fee_amount', 'ref_id', 'bank_account',
         'get_withdraw_request_receive_time', 'gateway', 'get_risks')}),
        ('اطلاعات کاربر', {'fields': ('get_withdraw_request_iban', 'get_withdraw_request_user',
                                      'get_user')}),
        ('نظر', {'fields': ('comment',)})
    )
    list_filter = ('status', UserRialWithdrawRequestFilter, )
    ordering = ('-created', )
    readonly_fields = (
        'created', 'bank_account', 'amount', 'get_withdraw_request_iban', 'fee_amount', 'get_risks',
        'get_withdraw_request_user', 'get_withdraw_request_receive_time', 'get_user', 'login_activity'
    )

    list_display = ('bank_account', 'created', 'get_user', 'status', 'amount', 'gateway', 'ref_id')

    actions = ('resend_withdraw_request', 'accept_withdraw_request', 'reject_withdraw_request', 'refund')

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

    @admin.display(description='risks')
    def get_risks(self, transfer):
        if not transfer.risks:
            return
        html = '<table dir="ltr"><tr><th>Factor</th><th>Value</th><th>Expected</th><th>Whitelist</th></tr>'

        for risk in transfer.risks:
            risk_dict = RiskFactor(**risk).__dict__
            risk_dict['value'] = humanize_number(risk_dict['value'])
            risk_dict['expected'] = humanize_number(risk_dict['expected'])

            html += '<tr><td>{reason}</td><td>{value}</td><td>{expected}</td><td>{whitelist}</td></tr>'.format(
                **risk_dict
            )

        html += '</table>'

        return mark_safe(html)

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

    @admin.action(description='تایید برداشت', permissions=['view'])
    def accept_withdraw_request(self, request, queryset):
        valid_qs = queryset.filter(status=FiatWithdrawRequest.INIT)

        for fiat_withdraw in valid_qs:
            fiat_withdraw.change_status(FiatWithdrawRequest.PROCESSING)
            process_withdraw(fiat_withdraw.id)

    @admin.action(description='رد برداشت', permissions=['view'])
    def reject_withdraw_request(self, request, queryset):
        valid_qs = queryset.filter(status=FiatWithdrawRequest.INIT)

        for fiat_withdraw in valid_qs:
            fiat_withdraw.change_status(FiatWithdrawRequest.CANCELED)

    @admin.action(description='refund', permissions=['change'])
    def refund(self, request, queryset):
        valid_qs = queryset.filter(status=FiatWithdrawRequest.DONE)

        for fiat_withdraw in valid_qs:
            fiat_withdraw.refund()

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
    list_display = ('created', 'gateway', 'bank_card', 'amount', 'authority', 'payment')
    search_fields = ('bank_card__card_pan', 'amount', 'authority')
    readonly_fields = ('bank_card', 'login_activity' )
    list_filter = (PaymentRequestUserFilter,)


class PaymentUserFilter(SimpleListFilter):
    title = 'کاربر'
    parameter_name = 'user'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('user')
        if user is not None:
            return queryset.filter(user=user)
        else:
            return queryset


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('created', 'get_amount', 'get_fee', 'status', 'ref_id', 'ref_status', 'get_user',)
    list_filter = (PaymentUserFilter, 'status', )
    search_fields = ('ref_id', 'payment_request__bank_card__card_pan', 'amount',
                     'payment_request__authority')

    @admin.display(description='مقدار')
    def get_amount(self, payment: Payment):
        return humanize_number(payment.amount)

    @admin.display(description='کارمزد')
    def get_fee(self, payment: Payment):
        return humanize_number(payment.fee)

    @admin.display(description='کاربر')
    def get_user(self, payment: Payment):
        link = url_to_edit_object(payment.user)
        return mark_safe("<a href='%s'>%s</a>" % (link, payment.user.phone))


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


@admin.register(MarketingSource)
class MarketingSourceAdmin(admin.ModelAdmin):
    list_display = ('utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term')
    list_filter = ('utm_source', )


@admin.register(MarketingCost)
class MarketingCostAdmin(admin.ModelAdmin):
    list_display = ('source', 'date', 'cost')
    search_fields = ('source__utm_source', )


@admin.register(ManualTransfer)
class ManualTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'amount', 'bank_account', 'status')
    readonly_fields = ('status', )

    def save_model(self, request, obj: ManualTransfer, form, change):
        obj.save()

        if obj.status == ManualTransfer.PROCESS:
            handler = FiatWithdraw.get_withdraw_channel(obj.gateway)

            handler.create_withdraw(
                wallet_id=handler.gateway.wallet_id,
                receiver=obj.bank_account,
                amount=obj.amount,
                request_id='mt-%s' % obj.id
            )

            obj.status = ManualTransfer.DONE
            obj.save(update_fields=['status'])


@admin.register(PaymentIdRequest)
class PaymentIdRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'owner', 'status', 'amount', 'get_user', 'external_ref', 'source_iban', 'deposit_time')
    search_fields = ('owner__pay_id', 'owner__user__phone', 'external_ref', 'source_iban', 'bank_ref')
    list_filter = ('status',)
    actions = ('accept', )
    readonly_fields = ('owner', 'get_user')

    @admin.action(description='accept deposit', permissions=['change'])
    def accept(self, request, queryset):
        for payment_request in queryset.filter(status=PENDING):
            payment_request.accept()

    @admin.display(description='user')
    def get_user(self, payment_id_request: PaymentIdRequest):
        user = payment_id_request.owner.user
        link = url_to_edit_object(user)
        return mark_safe("<a href='%s'>%s</a>" % (link, user.get_full_name()))


@admin.register(PaymentId)
class PaymentIdAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'user', 'pay_id', 'verified')
    search_fields = ('user__phone', 'pay_id')
    list_filter = ('verified',)
    readonly_fields = ('user', )
    actions = ('check_status', )

    @admin.action(description='check status', permissions=['change'])
    def check_status(self, request, queryset):
        for payment_id in queryset.filter(verified=False):
            client = get_payment_id_client(payment_id.gateway)
            client.check_payment_id_status(payment_id)


@admin.register(GeneralBankAccount)
class GeneralBankAccountAdmin(admin.ModelAdmin):
    list_display = ('created', 'name', 'iban', 'bank', 'deposit_address')


@admin.register(BankPaymentRequest)
class BankPaymentRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'amount', 'ref_id', 'destination_type',)
    readonly_fields = ('group_id', 'get_receipt_preview', 'get_amount_preview')
    fields = ('destination_type', 'amount', 'receipt', 'ref_id', 'get_amount_preview', 'get_receipt_preview', 'user',
              'destination_id', 'group_id')
    actions = ('accept_payment', )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(userfeatureperm__feature=UserFeaturePerm.BANK_PAYMENT)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='receipt preview')
    def get_receipt_preview(self, req: BankPaymentRequest):
        if req.receipt:
            return mark_safe("<img src='%s' width='200' height='200' />" % req.receipt.url)

    @admin.display(description='amount preview')
    def get_amount_preview(self, req: BankPaymentRequest):
        return req.amount and humanize_number(req.amount)

    @admin.action(description='Accept')
    def accept_payment(self, request, queryset):
        for q in queryset.filter(payment__isnull=True, user__isnull=False, destination_id__isnull=False).exclude(ref_id=''):
            q.create_payment()
