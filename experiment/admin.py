from django.contrib import admin

from experiment.models.click import Click
from experiment.models.experiment import Experiment
from experiment.models.link import Link
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'active',)
    readonly_fields = ('variants_result', )
    list_filter = ('active', )


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'name', 'type', 'data', 'experiment')
    list_filter = ('type', 'experiment__name')
    search_fields = ('name', 'type', 'data', 'experiment__name')


@admin.register(VariantUser)
class VariantUserAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'variant', 'user', 'triggered', 'link')
    list_filter = ('variant', 'triggered')
    search_fields = ('variant__name', 'variant__type')


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('created', 'updated', 'token', 'user')
    search_fields = ('token', 'destination', 'user')


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ('created', 'user_agent')
