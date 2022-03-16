from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import F
from django.db.models import Q
from django.db.models import Sum
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin

from accounts.models import UserComment
from accounts.utils.admin import url_to_admin_list
from financial.models.bank_card import BankCard, BankAccount
from financial.models.payment import Payment
from financial.models.withdraw_request import FiatWithdrawRequest
from financial.utils.withdraw_limit import FIAT_WITHDRAW_LIMIT, get_fiat_withdraw_irt_value, CRYPTO_WITHDRAW_LIMIT, \
    get_crypto_withdraw_irt_value
from ledger.models import OTCRequest, OTCTrade
from ledger.models.wallet import Wallet
from ledger.utils.precision import humanize_number
from ledger.models.transfer import Transfer
from .admin_guard import M
from .admin_guard.admin import AdvancedAdmin
from .models import User, Account, Notification, FinotechRequest
from .tasks import basic_verify_user
from .tasks.verify_user import alert_user_verify_status
from .utils.validation import gregorian_to_jalali_date

MANUAL_VERIFY_CONDITION = Q(
    Q(first_name_verified=None) | Q(last_name_verified=None),
    national_code_verified=True,
    birth_date_verified=True,
    level=User.LEVEL1,
    verify_status=User.PENDING
)


class UserStatusFilter(SimpleListFilter):
    title = 'تایید سطح دو یا سه'
    parameter_name = 'status_is_pending_or_rejected'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('status_is_pending_or_rejected')
        if user is not None:
            return queryset.filter((Q(verify_status='pending') | Q(verify_status='rejected')))
        else:
            return queryset


class ManualNameVerifyFilter(SimpleListFilter):
    title = 'نیازمند تایید دستی نام'
    parameter_name = 'manual_name_verify'

    def lookups(self, request, model_admin):
        return (1, 'بله'), (0, 'خیر')

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:

            if value == '1':
                return queryset.filter(MANUAL_VERIFY_CONDITION)
            elif value == '0':
                return queryset.exclude(MANUAL_VERIFY_CONDITION)

        return queryset


class UserCommentInLine(admin.TabularInline):
    model = UserComment
    extra = 1


@admin.register(User)
class CustomUserAdmin(SimpleHistoryAdmin, AdvancedAdmin, UserAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'password': None,
        'first_name': ~M('first_name_verified'),
        'last_name': ~M('last_name_verified'),
        'national_code': M.superuser & ~M('national_code_verified'),
        'birth_date': M.superuser & ~M('birth_date_verified'),
        'selfie_image_verified': M.superuser | (M('selfie_image') & M.is_none('selfie_image_verified')),
    }

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'national_code', 'email', 'phone', 'birth_date',
                                         'get_birth_date_jalali',
                                         'telephone', 'get_national_card_image', 'get_selfie_image')}),
        (_('Authentication'), {'fields': ('level', 'verify_status', 'email_verified', 'first_name_verified',
                                          'last_name_verified', 'national_code_verified', 'birth_date_verified',
                                          'telephone_verified', 'selfie_image_verified',
                                          )}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': (
            'get_last_login_jalali', 'get_date_joined_jalali', 'get_first_fiat_deposit_date_jalali',
            'get_level_2_verify_datetime_jalali', 'get_level_3_verify_datetime_jalali',
        )}),
        (_('لینک های مهم'), {
            'fields': (
                'get_payment_address', 'get_withdraw_address',
                'get_otctrade_address', 'get_wallet_address', 'get_bank_card_link',
                'get_bank_account_link', 'get_transfer_link', 'get_finotech_request_link',
            )
        }),
        (_('اطلاعات مالی کاربر'), {'fields': (
            'get_sum_of_value_buy_sell', 'get_remaining_fiat_withdraw_limit', 'get_remaining_crypto_withdraw_limit'
        )}),
        (_("جایزه‌های دریافتی"), {'fields': ('get_user_prizes',)}
        )

    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'level')
    list_filter = (
        'is_staff', 'is_superuser', 'is_active', 'groups',
        ManualNameVerifyFilter, 'level', 'date_joined', 'verify_status', 'level_2_verify_datetime',
        'level_3_verify_datetime', UserStatusFilter)
    inlines = [UserCommentInLine,]
    ordering = ('-id', )
    actions = ('verify_user_name', 'reject_user_name')
    readonly_fields = (
        'get_payment_address', 'get_withdraw_address', 'get_otctrade_address', 'get_wallet_address',
        'get_sum_of_value_buy_sell', 'get_birth_date_jalali', 'get_national_card_image',
        'get_selfie_image', 'get_level_2_verify_datetime_jalali', 'get_level_3_verify_datetime_jalali',
        'get_first_fiat_deposit_date_jalali', 'get_date_joined_jalali', 'get_last_login_jalali',
        'get_remaining_fiat_withdraw_limit', 'get_remaining_crypto_withdraw_limit',
        'get_bank_card_link', 'get_bank_account_link', 'get_transfer_link', 'get_finotech_request_link',
        'get_user_prizes',
    )

    @admin.action(description='تایید نام کاربر', permissions=['view'])
    def verify_user_name(self, request, queryset):
        to_verify_users = queryset.filter(MANUAL_VERIFY_CONDITION).distinct()

        for user in to_verify_users:
            user.first_name_verified = True
            user.last_name_verified = True
            user.save()
            basic_verify_user.delay(user.id)

    @admin.action(description='رد کردن نام کاربر', permissions=['view'])
    def reject_user_name(self, request, queryset):
        to_reject_users = queryset.filter(MANUAL_VERIFY_CONDITION).distinct()

        for user in to_reject_users:
            user.change_status(User.REJECTED)
            alert_user_verify_status(user)

    def save_model(self, request, user: User, form, change):
        if not request.user.is_superuser:
            old_user = User.objects.get(id=user.id)
            if not old_user.is_superuser and user.is_superuser:
                raise Exception('Dangerous action happened!')

        return super(CustomUserAdmin, self).save_model(request, user, form, change)

    def get_payment_address(self, user: User):
        link = url_to_admin_list(Payment)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_payment_address.short_description = 'واریزهای ریالی'

    def get_withdraw_address(self, user: User):
        link = url_to_admin_list(FiatWithdrawRequest)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_withdraw_address.short_description = 'درخواست برداشت ریالی'

    def get_otctrade_address(self, user: User):
        link = url_to_admin_list(OTCTrade)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_otctrade_address.short_description = 'خریدهای OTC'

    def get_wallet_address(self, user: User):
        link = url_to_admin_list(Wallet) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_wallet_address.short_description = 'لیست کیف‌ها'

    def get_sum_of_value_buy_sell(self, user: User):
        value = OTCRequest.objects.filter(
            account__user_id=user.id,
            otctrade__isnull=False,
        ).aggregate(
            amount=Sum(F('to_price_absolute_irt') * F('to_amount'))
        )
        return humanize_number(int(value['amount'] or 0))
    get_sum_of_value_buy_sell.short_description = 'مجموع معاملات'

    def get_bank_card_link(self, user: User):
        link = url_to_admin_list(BankCard) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)

    get_bank_card_link.short_description = 'کارت‌های بانکی'

    def get_bank_account_link(self, user: User):
        link = url_to_admin_list(BankAccount) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)

    get_bank_account_link.short_description = 'حساب‌های بانکی'

    def get_transfer_link(self, user: User):
        link = url_to_admin_list(Transfer) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link) \

    get_transfer_link.short_description = 'تراکنش‌های رمزارزی'

    def get_finotech_request_link(self, user: User):
        link = url_to_admin_list(FinotechRequest) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)

    get_finotech_request_link.short_description = 'درخواست‌های فینوتک'

    def get_birth_date_jalali(self, user: User):
        return gregorian_to_jalali_date(user.birth_date).strftime('%Y/%m/%d')

    get_birth_date_jalali.short_description = 'تاریخ تولد شمسی'

    def get_level_2_verify_datetime_jalali(self, user: User):
        return gregorian_to_jalali_date(user.level_2_verify_datetime).strftime('%Y/%m/%d')

    get_level_2_verify_datetime_jalali.short_description = 'تاریخ تایید سطح ۲'

    def get_level_3_verify_datetime_jalali(self, user: User):
        return gregorian_to_jalali_date(user.level_3_verify_datetime).strftime('%Y/%m/%d')

    get_level_3_verify_datetime_jalali.short_description = 'تاریخ تایید سطح ۳'

    def get_first_fiat_deposit_date_jalali(self, user: User):
        return gregorian_to_jalali_date(user.first_fiat_deposit_date).strftime('%Y/%m/%d')

    get_first_fiat_deposit_date_jalali.short_description = 'تاریخ اولین واریز ریالی'

    def get_date_joined_jalali(self, user: User):
        return gregorian_to_jalali_date(user.date_joined).strftime('%Y/%m/%d')

    get_date_joined_jalali.short_description = 'تاریخ پیوستن'

    def get_last_login_jalali(self, user: User):
        return gregorian_to_jalali_date(user.last_login).strftime('%Y/%m/%d')

    get_last_login_jalali.short_description = 'آخرین ورود'

    def get_remaining_fiat_withdraw_limit(self, user: User):
        return humanize_number(FIAT_WITHDRAW_LIMIT[user.level] - get_fiat_withdraw_irt_value(user))

    get_remaining_fiat_withdraw_limit.short_description = 'باقی مانده سقف مجاز برداشت ریالی روزانه'

    def get_remaining_crypto_withdraw_limit(self, user: User):
        return humanize_number(CRYPTO_WITHDRAW_LIMIT[user.level] - get_crypto_withdraw_irt_value(user))

    get_remaining_crypto_withdraw_limit.short_description = 'باقی مانده سقف مجاز برداشت رمزارز   روزانه'

    def get_national_card_image(self, user: User):
        return mark_safe(
            "<img src='%s' width='200' height='200' />" % user.national_card_image.get_absolute_image_url()
        )

    get_national_card_image.short_description = 'عکس کارت ملی'

    def get_selfie_image(self, user: User):
        return mark_safe("<img src='%s' width='200' height='200' />" % user.selfie_image.get_absolute_image_url())

    get_selfie_image.short_description = 'عکس سلفی'

    def get_user_prizes(self, user: User):
        prizes = user.account.prize_set.all()
        prize_list = []
        for prize in prizes:
            prize_list.append(prize.scope)
        return prize_list

    get_user_prizes.short_description = ('جایزه‌های دریافتی کاربر')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')


class FinotechRequestUserFilter(SimpleListFilter):
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


@admin.register(FinotechRequest)
class FinotechRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'url', 'data', 'status_code')
    list_filter = (FinotechRequestUserFilter, )
    ordering = ('-created', )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'recipient', 'level', 'title', 'message')
    list_filter = ('level', 'recipient')
    search_fields = ('title', 'message', )


@admin.register(UserComment)
class UserCommentAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ['user', 'created']
