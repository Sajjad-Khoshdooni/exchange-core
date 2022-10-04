from django.contrib import admin
from gamify import models


@admin.register(models.MissionJourney)
class MissionJourneyAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    list_editable = ('active', )


class TaskInline(admin.TabularInline):
    fields = ('scope', 'type', 'max', 'title', 'link', 'description', 'level', 'order')
    model = models.Task
    extra = 0


class AchievementInline(admin.TabularInline):
    fields = ('scope', )
    model = models.Achievement
    extra = 0


@admin.register(models.Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('name', 'journey', 'active', 'get_tasks', 'achievement', 'order')
    list_editable = ('order', 'active')
    inlines = (TaskInline, AchievementInline)

    @admin.display(description='tasks')
    def get_tasks(self, mission: models.Mission):
        return ','.join(mission.task_set.values_list('scope', flat=True))
