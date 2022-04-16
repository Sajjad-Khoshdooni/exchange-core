from django.contrib import admin

from trader.models import MovingAverage


@admin.register(MovingAverage)
class MovingAverageAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'below', 'change_date', 'enable')
    list_editable = ('enable', )
