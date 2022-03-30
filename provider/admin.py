from django.contrib import admin

from provider import models


@admin.register(models.ProviderOrder)
class ProviderOrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'side', 'market', 'amount', 'order_id')
    search_fields = ('asset__symbol', 'order_id')


@admin.register(models.ProviderTransfer)
class ProviderTransferAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'network', 'amount', 'address', 'provider_transfer_id', 'caller_id')
    search_fields = ('asset__symbol', 'caller_id')


@admin.register(models.ProviderHedgedOrder)
class ProviderHedgedOrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'asset', 'side', 'amount', 'caller_id', 'hedged')
    search_fields = ('asset__symbol', 'caller_id')
