from django.db import models


class DailyAnalytics(models.Model):
    created = models.DateTimeField(unique=True, db_index=True)
    active_30 = models.PositiveSmallIntegerField()
    churn_30 = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = verbose_name_plural = 'Daily analytics'
