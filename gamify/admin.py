from django.contrib import admin

from gamify import models
from gamify.utils import clone_mission_template


@admin.register(models.MissionJourney)
class MissionJourneyAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'default')
    list_editable = ('active', 'default')


@admin.register(models.Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ('mission', 'asset', 'amount', 'voucher')


class TaskInline(admin.TabularInline):
    fields = ('scope', 'type', 'max', 'title', 'link', 'app_link', 'description', 'level', 'order')
    model = models.Task
    extra = 0


class AchievementInline(admin.TabularInline):
    fields = ('asset', 'amount', 'voucher')
    model = models.Achievement
    extra = 0


@admin.register(models.MissionTemplate)
class MissionTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'journey', 'active', 'get_tasks', 'achievement', 'order')
    list_editable = ('order', 'active')
    inlines = (TaskInline, AchievementInline)
    actions = ('clone_mission', )
    list_filter = ('journey', )
    ordering = ('-id', )

    @admin.display(description='tasks')
    def get_tasks(self, mission: models.MissionTemplate):
        return ','.join(mission.task_set.values_list('scope', flat=True))

    @admin.action(description='clone', permissions=['change'])
    def clone_mission(self, request, queryset):
        for mission in queryset:
            clone_mission_template(mission)


@admin.register(models.UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission')
    readonly_fields = ('user', )
    list_filter = ('mission', )


@admin.register(models.Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('mission', 'scope', 'title', 'type', 'max')
    list_filter = ('mission', )
