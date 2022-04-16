from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from market.models import *
from ledger.models import Asset


class BaseAssetFilter(SimpleListFilter):                                           
      title = 'Base Asset'                                                           
      parameter_name = 'base_asset'

      def lookups(self, request, model_admin):                                        
          assets = set([t for t in Asset.objects.filter(symbol__in=(Asset.USDT, Asset.IRT))])       
          return zip(assets, assets)                                                    

      def queryset(self, request, queryset):                                          
          if self.value():                                                            
              return queryset.filter(base_asset__symbol=self.value())
          else:                                                                       
              return queryset                                                         


@admin.register(PairSymbol)
class PairSymbolAdmin(admin.ModelAdmin):
    list_display = ('name', 'enable', 'market_maker_enabled', 'maker_amount', 'taker_fee', 'maker_fee',)
    list_editable = ('enable',)
    list_filter = ('enable', BaseAssetFilter, 'market_maker_enabled',)
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
    list_display = ('created', 'type', 'symbol', 'side', 'fill_type', 'status', 'price', 'amount', 'wallet')
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
    list_display = ('created', 'symbol', 'amount', 'price', 'irt_value')
    list_filter = (MatchTypeFilter, 'symbol',)
    readonly_fields = ('symbol', 'taker_order', 'maker_order')
