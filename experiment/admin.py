from django.contrib import admin

from experiment.models.click import Click
from experiment.models.experiment import Experiment
from experiment.models.link import Link
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'a_variant', 'b_variant', 'active')
    list_filter = ('active', )
    search_fields = ('a_variant__name', 'b_variant__name', 'a_variant__type', 'b_variant__type',)


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'name', 'type', 'data')
    list_filter = ('type', )
    search_fields = ('name', 'type', 'data',)


@admin.register(VariantUser)
class VariantUserAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'variant', 'user', 'is_done', 'link')
    list_filter = ('variant', 'is_done')
    search_fields = ('variant__name', 'variant__type')


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'token', 'destination', 'user')
    list_filter = ('destination', )
    search_fields = ('token', 'destination', 'user')


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'user_agent')
