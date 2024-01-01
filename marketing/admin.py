from django.conf import settings
from django.contrib import admin

from marketing.models import AdsReport, CampaignPublisherReport

if settings.BRAND_EN.lower() == 'raastin':
    @admin.register(AdsReport)
    class AdsReportAdmin(admin.ModelAdmin):
        list_display = ('created', 'type', 'utm_campaign', 'utm_term', 'views', 'clicks', 'cost')
        list_filter = ('type', 'utm_campaign')
        search_fields = ('utm_term', )

    @admin.register(CampaignPublisherReport)
    class CampaignPublisherReportAdmin(admin.ModelAdmin):
        list_display = ('created', 'type', 'utm_campaign', 'utm_content', 'views', 'clicks', 'cost')
        list_filter = ('type', 'utm_campaign')
        search_fields = ('utm_content', )
