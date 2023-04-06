from django.contrib import admin

from analytics.models import ActiveTrader


@admin.register(ActiveTrader)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('created', 'period', 'active', 'churn', 'new')
