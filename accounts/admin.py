from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Account, BasicAccountInfo, Notification

admin.site.register(User, UserAdmin)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')


@admin.register(BasicAccountInfo)
class BasicAccountInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'national_card_code', 'verifier_code')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'level', 'message')
    list_filter = ('level', 'recipient')
    search_fields = ('message', )
