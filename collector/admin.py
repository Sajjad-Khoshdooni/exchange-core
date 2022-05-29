from django.contrib import admin

from collector.models import CoinMarketCap, BinanceIncome


@admin.register(CoinMarketCap)
class CoinMarketCapAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'cmc_rank', 'internal_id', 'name', 'slug', 'price', 'market_cap')
    search_fields = ('symbol', )
    ordering = ('cmc_rank', )


@admin.register(BinanceIncome)
class BinanceIncomeAdmin(admin.ModelAdmin):
    list_display = ('income_date', 'income_type', 'income', 'asset', 'symbol')
    search_fields = ('symbol', )
    list_filter = ('income_type', )
    ordering = ('-income_date', )
