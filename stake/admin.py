from django.contrib import admin
from django.utils.safestring import mark_safe

from accounts.models import User
from accounts.utils.admin import url_to_admin_list
from ledger.utils.precision import get_presentation_amount
from .models import StakeRequest, StakeRevenue, StakeOption
# Register your models here.


@admin.register(StakeOption)
class StakeOptionAdmin(admin.ModelAdmin):
    list_display = ['asset', 'apr', 'get_stake_request_number', 'total_cap', 'enable', 'landing']
    list_editable = ('enable', 'landing')

    readonly_fields = ('get_stake_request_number',)

    def get_stake_request_number(self, stake_option: StakeOption):
        return StakeRequest.objects.filter(
            stake_option=stake_option,
            status__in=(StakeRequest.DONE, StakeRequest.PENDING, StakeRequest.PROCESS)
        ).count()
    get_stake_request_number.short_description = 'تعداد درخواست های ثبت شده'


@admin.register(StakeRequest)
class StakeRequestAdmin(admin.ModelAdmin):
    list_display = ['get_stake_option_asset', 'get_amount', 'get_user','status']
    actions = ('stake_request_processing', 'stake_request_done',
               'stake_request_cancel_processing', 'stake_request_cancel_done',)
    readonly_fields = ('get_stake_option_asset', 'account', 'status', 'stake_option', 'get_amount', 'amount', 'get_user')

    def get_stake_option_asset(self, stake_request: StakeRequest):
        return stake_request.stake_option.asset
    get_stake_option_asset.short_description = 'asset'

    def get_amount(self, stake_request: StakeRequest):
        return get_presentation_amount(stake_request.amount)
    get_amount.short_description = 'amount'

    def get_user(self, stake_request: StakeRequest):
        user = stake_request.account.user
        link = url_to_admin_list(User) + '{}/change'.format(user.id)
        return mark_safe("<a href='%s'>%s</a>" % (link, user))
    get_user.short_description = 'user'

    @admin.action(description='بردن به حالت در انتظار', permissions=['view'])
    def stake_request_processing(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.PROCESS)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.PENDING)

    @admin.action(description='بردن به حالت انجام شده', permissions=['view'])
    def stake_request_done(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.PENDING)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.DONE)

    @admin.action(description='بردن به حالت لغو در حال انجام', permissions=['view'])
    def stake_request_cancel_processing(self, request, queryset):
        queryset = queryset.filter(status=StakeRequest.CANCEL_PROCESS)
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.CANCEL_PENDING)

    @admin.action(description='بردن به حالت لغو تکمیل شده', permissions=['view'])
    def stake_request_cancel_done(self, request, queryset):
        queryset = queryset.filter(status__in=(StakeRequest.CANCEL_PENDING, StakeRequest.CANCEL_PROCESS))
        for stake_request in queryset:
            stake_request.change_status(StakeRequest.CANCEL_COMPLETE)


@admin.register(StakeRevenue)
class StakeRevenueAdmin(admin.ModelAdmin):
    list_display = ['get_revenue', 'get_user', 'get_stake_option_asset', 'get_stake_option_apr']

    def get_revenue(self, stake_revenue: StakeRevenue):
        return get_presentation_amount(stake_revenue.revenue)

    def get_user(self, stake_revenue: StakeRevenue):
        user = stake_revenue.stake_request.account.user
        link = url_to_admin_list(User) + '{}/change'.format(user.id)
        return mark_safe("<a href='%s'>%s</a>" % (link, user))
    get_user.short_description = 'user'

    def get_stake_option_apr(self, stake_revenue: StakeRevenue):
        return get_presentation_amount(stake_revenue.stake_request.stake_option.apr)
    get_stake_option_apr.short_description = 'apr'

    def get_stake_option_asset(self, stake_revenue: StakeRevenue):
        return stake_revenue.stake_request.stake_option.asset
    get_stake_option_asset.short_description = 'asset'
