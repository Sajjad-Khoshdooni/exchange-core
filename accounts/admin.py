from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, Account, BasicAccountInfo, Notification


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'verification', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'verification')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'verification')


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')


@admin.register(BasicAccountInfo)
class BasicAccountInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'national_card_code', 'verifier_code')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('created', 'recipient', 'level', 'title', 'message')
    list_filter = ('level', 'recipient')
    search_fields = ('title', 'message', )
