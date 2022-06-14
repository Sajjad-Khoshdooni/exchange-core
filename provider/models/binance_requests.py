from django.db import models


class BinanceRequests(models.Model):

    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    status_code = models.PositiveSmallIntegerField(default=0, verbose_name='وضعیت')
    url = models.CharField(max_length=256)
    data = models.JSONField(blank=True, null=True)
    method = models.CharField(max_length=8)
    response = models.JSONField(blank=True, null=True)


