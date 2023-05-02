from django.db import models

from accounts.models import User


class TrafficSource(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='کاربر')

    utm_source = models.CharField(max_length=256)
    utm_medium = models.CharField(max_length=256)
    utm_campaign = models.CharField(max_length=256)
    utm_content = models.CharField(max_length=256)
    utm_term = models.CharField(max_length=256)
    gps_adid = models.CharField(max_length=256)

    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=256, blank=True)

    class Meta:
        verbose_name_plural = verbose_name = "منشا ترافیک"
        permissions = [
            ("read_yektanet_mobile", "Can read yektanet mobile analytics"),
            ("read_mediaad", "Can read mediaad analytics"),
        ]

    def __str__(self):
        return 'نظرهای ' + str(self.user)
