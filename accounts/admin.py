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
from financial.models.payment import Payment
from financial.models.withdraw_request import FiatWithdrawRequest
from ledger.models import OTCRequest, OTCTrade
from ledger.models.wallet import Wallet
from ledger.utils.precision import humanize_number
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
    }

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'national_code', 'email','phone', 'birth_date',
                                         'get_birth_date_jalali',
                                         'telephone', 'get_national_card_image', 'get_selfie_image')}),
        (_('Authentication'), {'fields': ('level', 'verify_status', 'email_verified', 'first_name_verified',
                                          'last_name_verified', 'national_code_verified', 'birth_date_verified',
                                          'telephone_verified', 'national_card_image_verified', 'selfie_image_verified',
                                          )}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'first_fiat_deposit_date')}),
        (_('لینک های مالی کاربر'),{'fields': ('get_payment_address','get_withdraw_address','get_otctrade_address','get_wallet_address')}),
        (_('مجموع خرید و فروش کاربر'),{'fields':('get_sum_of_value_buy_sell',)})

    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'level')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', ManualNameVerifyFilter, 'level', 'verify_status')
    inlines = [UserCommentInLine,]
    ordering = ('-id', )
    actions = ('verify_user_name', 'reject_user_name')
    readonly_fields = ('get_payment_address','get_withdraw_address','get_otctrade_address','get_wallet_address',
                       'get_sum_of_value_buy_sell', 'get_birth_date_jalali', 'get_national_card_image',
                       'get_selfie_image')

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
        return mark_safe ("<a href='%s'>دیدن</a>" % link)
    get_payment_address.short_description = 'واریزهای ریالی'

    def get_withdraw_address(self, user: User):
        link = url_to_admin_list(FiatWithdrawRequest)+'?user={}'.format(user.id)
        return mark_safe ("<a href='%s'>دیدن</a>" % link)
    get_withdraw_address.short_description = 'درخواست برداشت ریالی'

    def get_otctrade_address(self, user: User):
        link = url_to_admin_list(OTCTrade)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_otctrade_address.short_description = 'OTC_Trade'

    def get_wallet_address(self,user:User):
        link = url_to_admin_list(Wallet) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" %link)
    get_wallet_address.short_description = 'آدرس کیف اعتباری'

    def get_sum_of_value_buy_sell(self,user:User):
        value = OTCRequest.objects.filter(
            account__user_id=user.id
        ).aggregate(
            amount=Sum(F('to_price_abs') * F('to_amount'))
        )
        return humanize_number(float(value['amount'] or 0))
    get_sum_of_value_buy_sell.short_description = 'مجموع معاملات'

    def get_birth_date_jalali(self, user: User):
        return gregorian_to_jalali_date(user.birth_date).strftime('%Y/%m/%d')

    get_birth_date_jalali.short_description = 'تاریخ تولد شمسی'

    def get_national_card_image(self, user: User):
        return mark_safe("<img src='%s' width='200' height='200' />" % user.national_card_image.get_absolute_image_url())

    get_national_card_image.short_description = 'عکس کارت ملی'

    def get_selfie_image(self, user: User):
        return mark_safe("<img src='%s' width='200' height='200' />" % user.selfie_image.get_absolute_image_url())

    get_selfie_image.short_description = 'عکس سلفی'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')


@admin.register(FinotechRequest)
class FinotechRequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'url', 'data', 'status_code')
    ordering = ('-created', )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'recipient', 'level', 'title', 'message')
    list_filter = ('level', 'recipient')
    search_fields = ('title', 'message', )


@admin.register(UserComment)
class UserCommentAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ['user', 'created']
