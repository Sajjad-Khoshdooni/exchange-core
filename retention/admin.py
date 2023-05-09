from django.contrib import admin

from retention.models import Link, Click


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'token', 'user')
    search_fields = ('token', 'destination', 'user')


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ('created', 'user_agent')
