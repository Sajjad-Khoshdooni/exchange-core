from django.db import models

from django.contrib.sessions.models import Session


class LoginActivity(models.Model):
    TABLET, MOBILE, PC, UNKNOWN = 'tablet', 'mobile', 'pc', 'unknown'
    DEVICE_TYPE = ((TABLET, TABLET), (MOBILE, MOBILE), (PC, PC), (UNKNOWN, UNKNOWN))

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField()

    is_sign_up = models.BooleanField(default=False)

    user_agent = models.TextField(blank=True)
    device = models.CharField(blank=True, max_length=200)
    device_type = models.CharField(choices=DEVICE_TYPE, default=UNKNOWN, max_length=16)
    location = models.CharField(blank=True, max_length=200)
    os = models.CharField(blank=True, max_length=200)
    browser = models.CharField(blank=True, max_length=200)
    session = models.ForeignKey(Session, null=True, blank=True, on_delete=models.SET_NULL)
    city = models.CharField(blank=True, max_length=256)
    country = models.CharField(blank=True, max_length=256)
    ip_data = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name_plural = verbose_name = "تاریخچه ورود به حساب"
