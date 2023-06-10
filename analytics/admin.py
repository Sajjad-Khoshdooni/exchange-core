from django.contrib import admin

from analytics.models import ActiveTrader, ReportPermission


@admin.register(ActiveTrader)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('created', 'period', 'active', 'churn', 'new')


@admin.register(ReportPermission)
class ReportPermissionAdmin(admin.ModelAdmin):
    list_display = ('created', 'user', 'utm_source', 'utm_medium')
