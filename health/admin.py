from django.contrib import admin
from django.utils.safestring import mark_safe

from health.models import AlertType


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = ('type', 'warning_threshold', 'get_status')

    @admin.display(description='status', )
    def get_status(self, alert_type: AlertType):
        status = alert_type.get_status()

        colors = {status.IDLE: 'green', status.WARNING: 'orange', status.ERROR: 'red'}

        return mark_safe(f"<span style='color: {colors[status.status]}'>{status}</span>")
