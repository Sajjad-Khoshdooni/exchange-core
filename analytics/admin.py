from django.contrib import admin

from analytics.models import DailyAnalytics


@admin.register(DailyAnalytics)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('created', 'active_30', 'churn_30')
