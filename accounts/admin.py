from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Account

admin.site.register(User, UserAdmin)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'type')