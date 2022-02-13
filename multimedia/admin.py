from django.contrib import admin

# Register your models here.
from multimedia.models import Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'image')
    search_fields = ('uuid', )