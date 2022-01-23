from django.contrib import admin

from tracker.models import BlockTracker


@admin.register(BlockTracker)
class BlockTrackerAdmin(admin.ModelAdmin):
    list_display = ('created', 'number', 'hash', 'block_date')
