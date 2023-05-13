from django.contrib import admin

from gamify import models


@admin.register(models.MissionJourney)
class MissionJourneyAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'default')
    list_editable = ('active', 'default')


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

    @admin.display(description='tasks')
    def get_tasks(self, mission: models.MissionTemplate):
        return ','.join(mission.task_set.values_list('scope', flat=True))


@admin.register(models.UserMission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission')
