from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from .models import User, Account, Notification, FinotechRequest
from .tasks import basic_verify_user
from .tasks.verify_user import alert_user_verify_status


MANUAL_VERIFY_CONDITION = Q(
    ~Q(first_name_verified=True) | ~Q(last_name_verified=True),
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


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name','national_code', 'email','phone','birth_date')}),
        (_('Authentication'), {'fields': ('level','verify_status','email_verified','first_name_verified','last_name_verified','national_code_verified','birth_date_verified', )}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'first_fiat_deposit_date')}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'level')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', ManualNameVerifyFilter, 'level', 'verify_status')
    ordering = ('-id', )
    actions = ('verify_user_name', 'reject_user_name')

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
