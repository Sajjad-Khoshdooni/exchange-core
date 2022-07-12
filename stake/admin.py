from django.contrib import admin
from .models import StakeRequest, StakeRevenue, StakeOption
# Register your models here.


@admin.register(StakeOption)
class StakeOptionAdmin(admin.ModelAdmin):
    list_display = ['asset', 'apr', 'get_stake_request_number']

    readonly_fields = ('get_stake_request_number',)

    def get_stake_request_number(self, stake_option: StakeOption):
        return StakeRequest.objects.filter(stake_option=stake_option).count()
    get_stake_request_number.short_description = 'تعداد درخواست های ثبت شده'


@admin.register(StakeRequest)
class StakeRequestAdmin(admin.ModelAdmin):
    list_display = ['get_stake_option_asset', 'amount', 'status', 'id']

    readonly_fields = ('get_stake_option_asset',)

    def get_stake_option_asset(self, stake_request: StakeRequest):
        return stake_request.stake_option.asset
    get_stake_option_asset.short_description = 'asset'


@admin.register(StakeRevenue)
class StakeRevenueAdmin(admin.ModelAdmin):
    list_display = ['revenue', 'stake_request']
    pass
