from django.contrib import admin
from django.db.models import F

from multimedia.models import Image, Banner


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'image')
    search_fields = ('uuid', )


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'image', 'link', 'order', 'active')
    list_editable = ('active', 'order')

    def save_model(self, request, obj, form, change):
        if Banner.objects.filter(order=obj.order).exclude(id=obj.id).exists():
            Banner.objects.filter(order__gte=obj.order).exclude(id=obj.id).update(order=F('order') + 1)

        return super(BannerAdmin, self).save_model(request, obj, form, change)

