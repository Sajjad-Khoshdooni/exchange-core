from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from market.models import *


@admin.register(PairSymbol)
class PairSymbolAdmin(admin.ModelAdmin):
    list_display = ('name', 'enable', 'market_maker_enabled', 'maker_amount', 'taker_fee', 'maker_fee',)
    list_editable = ('enable',)
    list_filter = ('enable', 'base_asset', 'market_maker_enabled',)
    readonly_fields = ('name',)


class TypeFilter(SimpleListFilter):
    title = "type"
    parameter_name = "type"

    def lookups(self, request, model_admin):
        return [
            (Order.ORDINARY, 'Only ordinary'),
            ('system', 'System Maker Orders'),
            ('all', 'All orders')
        ]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.filter(type=Order.ORDINARY)
        if self.value() == 'system':
            return queryset.exclude(type=Order.ORDINARY)
        return queryset


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'type', 'symbol', 'side', 'fill_type', 'status', 'price', 'amount',)
    list_filter = (TypeFilter, 'side', 'fill_type', 'status', 'symbol',)


class MatchTypeFilter(SimpleListFilter):
    title = "match_type"
    parameter_name = "match_type"

    def lookups(self, request, model_admin):
        return [
            (Order.ORDINARY, 'Only ordinary'),
            ('system', 'System Maker Orders'),
            ('all', 'All orders')
        ]

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset.filter(taker_order__type=Order.ORDINARY, maker_order__type=Order.ORDINARY)
        if self.value() == 'system':
            return queryset.exclude(taker_order__type=Order.ORDINARY, maker_order__type=Order.ORDINARY)
        return queryset


@admin.register(FillOrder)
class FillOrderAdmin(admin.ModelAdmin):
    list_display = ('created', 'symbol', 'amount', 'price',)
    list_filter = (MatchTypeFilter, 'symbol',)
