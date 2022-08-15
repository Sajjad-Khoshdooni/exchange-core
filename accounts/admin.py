from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.db.models import Sum
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from jalali_date.admin import ModelAdminJalaliMixin
from simple_history.admin import SimpleHistoryAdmin

from accounts.models import CustomToken, FirebaseToken, ExternalNotification
from accounts.models import UserComment, TrafficSource, Referral
from accounts.utils.admin import url_to_admin_list, url_to_edit_object
from financial.models.bank_card import BankCard, BankAccount
from financial.models.payment import Payment
from financial.models.withdraw_request import FiatWithdrawRequest
from financial.utils.withdraw_limit import FIAT_WITHDRAW_LIMIT, get_fiat_withdraw_irt_value, CRYPTO_WITHDRAW_LIMIT, \
    get_crypto_withdraw_irt_value
from ledger.models import OTCTrade, DepositAddress
from ledger.models.transfer import Transfer
from ledger.models.wallet import Wallet
from ledger.utils.precision import get_presentation_amount
from ledger.utils.precision import humanize_number
from ledger.utils.price import BUY
from market.models import Trade, ReferralTrx, Order
from .admin_guard import M
from .admin_guard.admin import AdvancedAdmin
from .models import User, Account, Notification, FinotechRequest
from .models.login_activity import LoginActivity
from .tasks import basic_verify_user
from .utils.validation import gregorian_to_jalali_date_str, gregorian_to_jalali_datetime_str
from .verifiers.legal import is_48h_rule_passed

MANUAL_VERIFY_CONDITION = Q(
    Q(first_name_verified=None) | Q(last_name_verified=None),
    national_code_verified=True,
    birth_date_verified=True,
    level=User.LEVEL1,
    verify_status=User.PENDING
)


class UserStatusFilter(SimpleListFilter):
    title = 'تایید سطح دو '
    parameter_name = 'status_is_pending_or_rejected'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('status_is_pending_or_rejected')
        if user is not None:
            return queryset.filter((Q(verify_status='pending') | Q(verify_status='rejected')))
        else:
            return queryset


class UserPendingStatusFilter(SimpleListFilter):
    title = 'تایید سطح  سه'
    parameter_name = 'status_is_pending'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):
        user = request.GET.get('status_is_pending')
        if user is not None:
            return queryset.filter(verify_status='pending')
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


class UserNationalCodeFilter(SimpleListFilter):
    title = 'کد ملی'
    parameter_name = 'national_code'

    def lookups(self, request, model_admin):
        return (1, 1),

    def queryset(self, request, queryset):
        national_code = request.GET.get('national_code')
        if national_code is not None:
            return queryset.filter(national_code=national_code).exclude(national_code='')
        else:
            return queryset


class AnotherUserFilter(SimpleListFilter):
    title = 'دیگر کاربرها'
    parameter_name = 'user_id_exclude'

    def lookups(self, request, model_admin):
        return (1, 1),

    def queryset(self, request, queryset):
        user_id = request.GET.get('user_id_exclude')
        if user_id is not None:
            return queryset.exclude(id=user_id)
        else:
            return queryset


class UserCommentInLine(admin.TabularInline):
    model = UserComment
    extra = 1


class ExternalNotificationInLine(admin.TabularInline):
    model = ExternalNotification
    extra = 0
    fields = ('created', 'scope', )
    readonly_fields = ('created', 'scope', )
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class NotificationInLine(admin.TabularInline):
    model = Notification
    extra = 0
    fields = ('created', 'title', 'link', 'message', 'read_date')
    readonly_fields = ('created', 'title', 'link', 'message', 'read_date' )
    can_delete = False

    def has_add_permission(self, request, obj):
        return False


class UserReferredFilter(SimpleListFilter):
    title = 'لیست کاربران دعوت شده'
    parameter_name = 'owner_id'

    def lookups(self, request, model_admin):
        return [(1, 1)]

    def queryset(self, request, queryset):

        owner_id = request.GET.get('owner_id')
        if owner_id is not None:
            return queryset.filter(account__referred_by__owner__user__id=owner_id)
        else:
            return queryset


@admin.register(User)
class CustomUserAdmin(ModelAdminJalaliMixin, SimpleHistoryAdmin, AdvancedAdmin, UserAdmin):
    default_edit_condition = M.superuser

    fields_edit_conditions = {
        'password': None,
        'first_name': ~M('first_name_verified'),
        'last_name': ~M('last_name_verified'),
        'national_code': M.superuser | ~M('national_code_verified'),
        'national_code_phone_verified': True,
        'birth_date': M.superuser | ~M('birth_date_verified'),
        'selfie_image_verified': M.superuser | M('selfie_image'),
        'selfie_image_discard_text': M.superuser | (M('selfie_image') & M.is_none('selfie_image_verified')),
        'first_name_verified': M.is_none('first_name_verified'),
        'last_name_verified': M.is_none('last_name_verified'),
        'national_code_verified': ~M('national_code_verified'),
        'birth_date_verified': M.is_none('birth_date_verified'),
        'withdraw_before_48h_option': True,
        'allow_level1_crypto_withdraw': True,
    }

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'national_code', 'email', 'phone', 'birth_date',

                                         'get_selfie_image', 'archived',
                                         'get_user_reject_reason', 'get_source_medium'
                                         )}),
        (_('Authentication'), {'fields': ('level', 'verify_status', 'first_name_verified',
                                          'last_name_verified', 'national_code_verified', 'national_code_phone_verified',
                                          'birth_date_verified', 'reject_reason',
                                          'selfie_image_verified', 'selfie_image_verifier',
                                          'selfie_image_discard_text',
                                          )}),
        (_('Permissions'), {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions', 'show_margin',
                'withdraw_before_48h_option', 'allow_level1_crypto_withdraw'
            ),
        }),
        (_('Important dates'), {'fields': (
            'get_last_login_jalali', 'get_date_joined_jalali', 'get_first_fiat_deposit_date_jalali',
            'get_level_2_verify_datetime_jalali', 'get_level_3_verify_datetime_jalali', 'get_selfie_image_uploaded',
            'margin_quiz_pass_date'
        )}),
        (_('لینک های مهم'), {
            'fields': (
                'get_wallet', 'get_transfer_link', 'get_payment_address',
                'get_withdraw_address', 'get_otctrade_address', 'get_fill_order_address',
                'get_open_order_address', 'get_deposit_address', 'get_bank_card_link',
                'get_bank_account_link', 'get_finotech_request_link',
                'get_user_with_same_national_code', 'get_referred_user', 'get_login_activity_link',
            )
        }),
        (_('اطلاعات مالی کاربر'), {'fields': (
            'get_sum_of_value_buy_sell', 'get_remaining_fiat_withdraw_limit',
            'get_remaining_crypto_withdraw_limit', 'get_last_trade', 'get_total_balance_irt_admin'
        )}),
        (_("جایزه‌های دریافتی"), {'fields': ('get_user_prizes',)}),
        (_("کدهای دعوت کاربر"), {'fields': (
            'get_revenue_of_referral', 'get_referred_count', 'get_revenue_of_referred')})
    )

    list_display = ('username', 'first_name', 'last_name', 'level', 'archived', 'get_user_reject_reason',
                    'verify_status', 'get_source_medium', 'get_referrer_user')
    list_filter = (
        'archived', ManualNameVerifyFilter, 'level', 'national_code_phone_verified', 'date_joined', 'verify_status', 'level_2_verify_datetime',
        'level_3_verify_datetime', UserStatusFilter, UserNationalCodeFilter, AnotherUserFilter, UserPendingStatusFilter,
        'is_staff', 'is_superuser', 'is_active', 'groups', UserReferredFilter
    )
    inlines = [UserCommentInLine, ExternalNotificationInLine, NotificationInLine]
    ordering = ('-id', )
    actions = ('verify_user_name', 'reject_user_name', 'archive_users', 'unarchive_users', 'reevaluate_basic_verify')
    readonly_fields = (
        'get_payment_address', 'get_withdraw_address', 'get_otctrade_address', 'get_wallet',
        'get_sum_of_value_buy_sell',
        'get_selfie_image', 'get_level_2_verify_datetime_jalali', 'get_level_3_verify_datetime_jalali',
        'get_first_fiat_deposit_date_jalali', 'get_date_joined_jalali', 'get_last_login_jalali',
        'get_remaining_fiat_withdraw_limit', 'get_remaining_crypto_withdraw_limit', 'get_deposit_address',
        'get_bank_card_link', 'get_bank_account_link', 'get_transfer_link', 'get_finotech_request_link',
        'get_user_reject_reason', 'get_user_with_same_national_code', 'get_user_prizes', 'get_source_medium',
        'get_fill_order_address', 'selfie_image_verifier', 'get_revenue_of_referral', 'get_referred_count',
        'get_revenue_of_referred', 'get_open_order_address', 'get_selfie_image_uploaded', 'get_referred_user',
        'get_login_activity_link', 'get_last_trade', 'get_total_balance_irt_admin'
    )
    preserve_filters = ('archived', )

    search_fields = (*UserAdmin.search_fields, 'national_code')

    @admin.action(description='تایید نام کاربر', permissions=['view'])
    def verify_user_name(self, request, queryset):
        to_verify_users = queryset.filter(level=User.LEVEL1).exclude(first_name='').exclude(last_name='')

        for user in to_verify_users:
            user.first_name_verified = True
            user.last_name_verified = True
            user.save()
            basic_verify_user.delay(user.id)

    @admin.action(description='شروع احراز هویت پایه کاربر', permissions=['change'])
    def reevaluate_basic_verify(self, request, queryset):
        to_verify_users = queryset.filter(level=User.LEVEL1).exclude(first_name='').exclude(last_name='')

        for user in to_verify_users:
            basic_verify_user.delay(user.id)

    @admin.action(description='رد کردن نام کاربر', permissions=['view'])
    def reject_user_name(self, request, queryset):
        to_reject_users = queryset.filter(MANUAL_VERIFY_CONDITION).distinct()

        for user in to_reject_users:
            user.change_status(User.REJECTED)

    @admin.action(description='بایگانی کاربر', permissions=['view'])
    def archive_users(self, request, queryset):
        queryset.update(archived=True)

    @admin.action(description='خارج کردن از بایگانی', permissions=['view'])
    def unarchive_users(self, request, queryset):
        queryset.update(archived=False)

    def save_model(self, request, user: User, form, change):
        old_user = User.objects.get(id=user.id)

        if not request.user.is_superuser:
            if not old_user.is_superuser and user.is_superuser:
                raise Exception('Dangerous action happened!')

        if not old_user.selfie_image_verified and user.selfie_image_verified:
            user.selfie_image_verifier = request.user

        return super(CustomUserAdmin, self).save_model(request, user, form, change)

    def get_payment_address(self, user: User):
        link = url_to_admin_list(Payment)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_payment_address.short_description = 'واریزهای ریالی'

    def get_fill_order_address(self, user: User):
        link = url_to_admin_list(Trade) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_fill_order_address.short_description = 'معاملات'

    def get_open_order_address(self, user: User):
        link = url_to_admin_list(Order) +'?status=new&user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_open_order_address.short_description = 'سفارشات باز'

    def get_withdraw_address(self, user: User):
        link = url_to_admin_list(FiatWithdrawRequest)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_withdraw_address.short_description = 'درخواست برداشت ریالی'

    def get_otctrade_address(self, user: User):
        link = url_to_admin_list(OTCTrade)+'?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_otctrade_address.short_description = 'خریدهای OTC'

    def get_source_medium(self, user: User):
        if hasattr(user, 'trafficsource'):
            link = url_to_edit_object(user.trafficsource)
            text = '%s/%s' % (user.trafficsource.utm_source, user.trafficsource.utm_medium)

            return mark_safe("<a href='%s'>%s</a>" % (link, text))
    get_source_medium.short_description = 'source/medium'

    def get_referrer_user(self, user: User):
        account = getattr(user, 'account', None)
        referrer = account and account.referred_by and account.referred_by.owner.user

        if referrer:
            link = url_to_edit_object(referrer)
            return mark_safe("<a href='%s'>%s</a>" % (link, referrer.id))

    get_referrer_user.short_description = 'referrer'

    def get_user_reject_reason(self, user: User):
        if user.level == User.LEVEL1 and user.verify_status == User.REJECTED and \
                user.reject_reason == User.NATIONAL_CODE_DUPLICATED:
            return 'کد ملی تکراری'

        verify_fields = [
            'national_code_verified', 'birth_date_verified', 'first_name_verified', 'last_name_verified',
            'bank_card_verified', 'bank_account_verified', 'selfie_image_verified'
        ]

        for verify_field in verify_fields:
            field = verify_field[:-9]

            if field == 'bank_card':
                bank_card = user.bankcard_set.all().order_by('-verified').first()
                value = bank_card and bank_card.verified
            elif field == 'bank_account':
                bank_account = user.bankaccount_set.all().order_by('-verified').first()
                value = bank_account and bank_account.verified
            else:
                value = getattr(user, verify_field)

            if not value:
                status = 'رد شده' if value is False else 'نامشخص'

                if field == 'bank_card':
                    reason = 'شماره کارت'
                elif field == 'bank_account':
                    reason = 'شماره حساب'
                else:
                    reason = getattr(User, field).field.verbose_name

                return reason + ' ' + status

        return ''

    get_user_reject_reason.short_description = 'وضعیت احراز'

    def get_wallet(self, user: User):
        link = url_to_admin_list(Wallet) + '?account={}'.format(user.account.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_wallet.short_description = 'لیست کیف‌ها'

    def get_sum_of_value_buy_sell(self, user: User):
        if not hasattr(user, 'account'):
            return 0

        return humanize_number(user.account.trade_volume_irt)

    get_sum_of_value_buy_sell.short_description = 'مجموع معاملات'

    def get_last_trade(self, user: User):
        return gregorian_to_jalali_datetime_str(Trade.objects.filter(account=user.account).last().created)
    get_last_trade.short_description = 'تاریخ آخرین معامله'

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

    def get_referred_user(self, user: User):

        link = url_to_admin_list(User) + '?owner_id={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_referred_user.short_description = 'کاربران دعوت شده'

    def get_login_activity_link(self, user: User):
        link = url_to_admin_list(LoginActivity) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_login_activity_link.short_description = 'تاریخچه ورود به حساب'

    def get_user_with_same_national_code(self, user: User):
        user_count = User.objects.filter(
            ~Q(id=user.id) & Q(national_code=user.national_code) & ~Q(national_code='')
        ).count()
        return mark_safe(
            "<a href='/admin/accounts/user/?national_code=%s&user_id_exclude=%s'> دیدن (%sکاربر)  </a>" % (
                user.national_code, user.id, user_count
            )
        )

    get_user_with_same_national_code.short_description = 'کاربرانی با این کد ملی'

    def get_level_2_verify_datetime_jalali(self, user: User):
        return gregorian_to_jalali_datetime_str(user.level_2_verify_datetime)

    get_level_2_verify_datetime_jalali.short_description = 'تاریخ تایید سطح ۲'

    def get_level_3_verify_datetime_jalali(self, user: User):
        return gregorian_to_jalali_datetime_str(user.level_3_verify_datetime)

    get_level_3_verify_datetime_jalali.short_description = 'تاریخ تایید سطح ۳'

    def get_first_fiat_deposit_date_jalali(self, user: User):
        date = gregorian_to_jalali_datetime_str(user.first_fiat_deposit_date)
        if is_48h_rule_passed(user):
            color = 'green'
        else:
            color = 'red'

        return mark_safe("<span style='color: %s'>%s</span>" % (color, date))

    get_first_fiat_deposit_date_jalali.short_description = 'تاریخ اولین واریز ریالی'

    def get_date_joined_jalali(self, user: User):
        return gregorian_to_jalali_date_str(user.date_joined)

    get_date_joined_jalali.short_description = 'تاریخ پیوستن'

    def get_last_login_jalali(self, user: User):
        return gregorian_to_jalali_date_str(user.last_login)

    get_last_login_jalali.short_description = 'آخرین ورود'

    def get_remaining_fiat_withdraw_limit(self, user: User):
        return humanize_number(FIAT_WITHDRAW_LIMIT[user.level] - get_fiat_withdraw_irt_value(user))

    get_remaining_fiat_withdraw_limit.short_description = 'باقی مانده سقف مجاز برداشت ریالی روزانه'

    def get_remaining_crypto_withdraw_limit(self, user: User):
        return humanize_number(CRYPTO_WITHDRAW_LIMIT[user.level] - get_crypto_withdraw_irt_value(user))

    get_remaining_crypto_withdraw_limit.short_description = 'باقی مانده سقف مجاز برداشت رمزارز   روزانه'

    def get_selfie_image(self, user: User):
        return mark_safe("<img src='%s' width='200' height='200' />" % user.selfie_image.get_absolute_image_url())

    get_selfie_image.short_description = 'عکس سلفی'

    def get_user_prizes(self, user: User):
        prizes = user.account.prize_set.all()
        prize_list = []
        for prize in prizes:
            prize_list.append(prize.scope)
        return prize_list

    get_user_prizes.short_description = 'جایزه‌های دریافتی کاربر'

    def get_referred_count(self, user: User):
        referrals = Referral.objects.filter(owner=user.account)
        referred_count = 0
        for referral in referrals:
            referred_count += Account.objects.filter(referred_by=referral).count()
        return referred_count
    get_referred_count.short_description = ' تعداد دوستان دعوت شده'

    def get_revenue_of_referral(self, user: User):
        referrals = Referral.objects.filter(owner=user.account)
        revenues = 0
        for referral in referrals:
            revenue = ReferralTrx.objects.filter(referral=referral).aggregate(total=Sum('referrer_amount'))
            revenues += int(revenue['total'] or 0)
        return revenues

    get_revenue_of_referral.short_description = 'درآمد حاصل از کدهای دعوت ارسال شده به دوستان '

    def get_revenue_of_referred(self, user: User):
        referral = user.account.referred_by

        revenue = ReferralTrx.objects.filter(referral=referral).aggregate(total=Sum('trader_amount'))
        return int(revenue['total'] or 0)

    get_revenue_of_referred.short_description = 'درآمد حاصل از کد دعوت استفاده شده'

    def get_selfie_image_uploaded(self, user: User):
        latest_null = user.history.filter(selfie_image__isnull=True).order_by('history_date').last()

        if latest_null:
            history = user.history.filter(
                history_id__gt=latest_null.history_id,
                selfie_image__isnull=False
            ).order_by('history_date').first()

            if history:
                return gregorian_to_jalali_datetime_str(history.history_date)

    get_selfie_image_uploaded.short_description = 'زمان آپلود عکس سلفی'

    def get_deposit_address(self, user: User):
        link = url_to_admin_list(DepositAddress) + '?user={}'.format(user.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)

    get_deposit_address.short_description = 'آدرس‌های کیف پول'

    def get_total_balance_irt_admin(self, user: User):
        total_balance_irt = user.account.get_total_balance_irt(side=BUY)
        
        return humanize_number(int(total_balance_irt))

    get_total_balance_irt_admin.short_description = 'دارایی به تومان'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'name', 'trade_volume_irt')
    search_fields = ('user__phone', )
    list_filter = ('type', 'primary')

    fieldsets = (
        ('اطلاعات', {'fields': (
            'name', 'user', 'type', 'primary', 'trade_volume_irt', 'get_wallet',
            'get_total_balance_irt_admin', 'get_total_balance_usdt_admin', 'referred_by'
        )}),
    )
    readonly_fields = ('user', 'get_wallet', 'get_total_balance_irt_admin', 'get_total_balance_usdt_admin',
                       'trade_volume_irt', 'referred_by')

    def get_wallet(self, account: Account):
        link = url_to_admin_list(Wallet) + '?account={}'.format(account.id)
        return mark_safe("<a href='%s'>دیدن</a>" % link)
    get_wallet.short_description = 'لیست کیف‌ها'

    def get_total_balance_irt_admin(self, account: Account):
        total_balance_irt = account.get_total_balance_irt(side=BUY)
        
        return humanize_number(int(total_balance_irt))

    get_total_balance_irt_admin.short_description = 'دارایی به تومان'

    def get_total_balance_usdt_admin(self, account: Account):
        total_blance_usdt = account.get_total_balance_usdt(market=Wallet.SPOT, side=BUY)
        return humanize_number(int(total_blance_usdt))

    get_total_balance_usdt_admin.short_description = 'دارایی به تتر'


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('owner', 'code', 'owner_share_percent')
    search_fields = ('code', 'owner__user__phone')


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
    readonly_fields = ('user', )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'recipient', 'level', 'title', 'message')
    list_filter = ('level', 'recipient')
    search_fields = ('title', 'message', )


@admin.register(UserComment)
class UserCommentAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ['user', 'created']


@admin.register(TrafficSource)
class TrafficSourceAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ['user', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
    search_fields = ['user__phone']


@admin.register(LoginActivity)
class LoginActivityAdmin(admin.ModelAdmin):
    list_display = ['created', 'user', 'ip', 'device', 'os', 'browser', 'device_type', 'is_sign_up']
    search_fields = ['user__phone', 'ip']
    readonly_fields = ('user', )


@admin.register(FirebaseToken)
class FirebaseTokenAdmin(SimpleHistoryAdmin, admin.ModelAdmin):
    list_display = ['user', 'token']
    readonly_fields = ('created',)


@admin.register(ExternalNotification)
class ExternalNotificationAdmin(admin.ModelAdmin):
    list_display = ['created', 'user', 'phone', 'scope']
