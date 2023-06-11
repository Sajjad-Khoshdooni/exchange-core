from django.contrib import admin

from analytics.models import ActiveTrader, EventTracker


@admin.register(ActiveTrader)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('created', 'period', 'active', 'churn', 'new')


@admin.register(EventTracker)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('created', 'type', 'last_id')
