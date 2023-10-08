from django.contrib import admin
from django.utils.safestring import mark_safe

from accounts.admin_guard.utils.html import get_table_html
from health.alert import ALERTS
from health.models import AlertType


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = ('type', 'get_status', 'warning_threshold', 'error_threshold')
    readonly_fields = ('get_type_help', )

    @admin.display(description='status', )
    def get_status(self, alert_type: AlertType):
        status = alert_type.get_status()

        colors = {status.OK: 'green', status.WARNING: 'darkorange', status.ERROR: 'red'}

        return mark_safe(f"<span style='color: {colors[status.type]}'>{status}</span>")

    @admin.display(description='type_help')
    def get_type_help(self, alert_type: AlertType):
        return mark_safe(get_table_html(['type', ('help', 'threshold help')], [{'type': a.NAME, 'help': a.HELP} for a in ALERTS.values()]))
