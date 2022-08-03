from django.contrib import admin
from .models import StakeRequest, StakeRevenue, StakeOption
# Register your models here.


@admin.register(StakeOption)
class StakeOptionAdmin(admin.ModelAdmin):
    list_display = ['asset', 'apr', 'get_stake_request_number', 'total_cap', 'enable', 'landing']
    list_editable = ('enable', 'landing')

    readonly_fields = ('get_stake_request_number',)

    def get_stake_request_number(self, stake_option: StakeOption):
        return StakeRequest.objects.filter(stake_option=stake_option).count()
    get_stake_request_number.short_description = 'تعداد درخواست های ثبت شده'


@admin.register(StakeRequest)
class StakeRequestAdmin(admin.ModelAdmin):
    list_display = ['get_stake_option_asset', 'amount', 'status']
    actions = ('stake_request_processing', 'stake_request_done',
               'stake_request_cancel_processing', 'stake_request_cancel_done',)
    readonly_fields = ('get_stake_option_asset',)

    def get_stake_option_asset(self, stake_request: StakeRequest):
        return stake_request.stake_option.asset
    get_stake_option_asset.short_description = 'asset'

    @admin.action(description='بردن به حالت در انتظار', permissions=['view'])
    def stake_request_processing(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.PROCESS)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.PENDING)

    @admin.action(description='بردن به حالت انجام شده', permissions=['view'])
    def stake_request_done(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.DONE)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.DONE)

    @admin.action(description='بردن به حالت لغو در حال پردازش', permissions=['view'])
    def stake_request_cancel_processing(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.CANCEL_PROCESS)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.CANCEL_PENDING)

    @admin.action(description='بردن به حالت لغو تکمیل شده', permissions=['view'])
    def stake_request_cancel_done(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.CANCEL_PENDING)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.CANCEL_COMPLETE)


@admin.register(StakeRevenue)
class StakeRevenueAdmin(admin.ModelAdmin):
    list_display = ['revenue', 'stake_request']

