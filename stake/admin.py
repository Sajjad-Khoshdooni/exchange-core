from django.contrib import admin
from stake import models
# Register your models here.


@admin.register(models.StakeOption)
class StakeOptionAdmin(admin.ModelAdmin):
    pass


@admin.register(models.StakeRequest)
class StakeRequestAdmin(admin.ModelAdmin):
    pass


@admin.register(models.StakeRevenue)
class StakeRevenueAdmin(admin.ModelAdmin):
    pass
