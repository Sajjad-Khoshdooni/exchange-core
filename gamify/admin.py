from django.contrib import admin
from django.db import transaction

from gamify import models
from gamify.utils import clone_model


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

    @admin.display(description='tasks')
    def get_tasks(self, mission: models.MissionTemplate):
        return ','.join(mission.task_set.values_list('scope', flat=True))

    @admin.action(description='clone', permissions=['change'])
    def clone_mission(self, request, queryset):
        with transaction.atomic():
            for mission in queryset:
                tasks = mission.task_set.all()
                achievement = mission.achievement

                new_mission = clone_model(mission)

                achievement.mission = new_mission
                clone_model(achievement)

                for task in tasks:
                    task.mission = new_mission
                    clone_model(task)


@admin.register(models.UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission')
    readonly_fields = ('user', )
    list_filter = ('mission', )
