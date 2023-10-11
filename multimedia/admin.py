from django.contrib import admin
from django.db.models import F
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin

from multimedia.models import Image, Banner, CoinPriceContent, Article, Section


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'get_selfie_image', 'image')
    search_fields = ('uuid',)

    def get_selfie_image(self, image: Image):
        return mark_safe("<img src='%s' width='200' height='200' />" % image.get_absolute_image_url())

    get_selfie_image.short_description = 'عکس'


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'image', 'link', 'app_link', 'order', 'active')
    list_editable = ('active', 'order')

    def save_model(self, request, obj, form, change):
        if Banner.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Banner.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(BannerAdmin, self).save_model(request, obj, form, change)


@admin.register(CoinPriceContent)
class CoinPriceContentAdmin(SimpleHistoryAdmin):
    pass


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title',)
    readonly_fields = ('slug',)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('title',)
    readonly_fields = ('slug',)
