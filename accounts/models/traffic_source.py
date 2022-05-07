from django.db import models
from simple_history.models import HistoricalRecords

from accounts.models import User


class TrafficSource(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='کاربر')

    utm_source = models.CharField(max_length=256)
    utm_medium = models.CharField(max_length=256)
    utm_campaign = models.CharField(max_length=256)
    utm_content = models.CharField(max_length=256)
    utm_term = models.CharField(max_length=256)

    class Meta:
        verbose_name_plural = verbose_name = "منشا ترافیک"

    def __str__(self):
        return 'نظرهای ' + str(self.user)
