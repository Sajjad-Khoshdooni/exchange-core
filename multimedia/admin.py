from django.contrib import admin

from multimedia.models import Image, Banner


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'image')
    search_fields = ('uuid', )


@admin.register(Banner)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'image', 'link', 'active')
    list_editable = ('active', )
