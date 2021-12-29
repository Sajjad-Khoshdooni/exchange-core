from django.contrib import admin
from ledger import models


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'name_fa')
