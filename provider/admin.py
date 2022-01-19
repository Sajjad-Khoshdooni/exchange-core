from django.contrib import admin

from provider import models


@admin.register(models.ProviderOrder)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'side', 'amount', 'order_id')
