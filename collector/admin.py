from django.contrib import admin

from collector.models import CoinMarketCap


@admin.register(CoinMarketCap)
class CoinMarketCapAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'internal_id', 'name', 'slug', 'price', 'market_cap')
    search_fields = ('symbol', )
