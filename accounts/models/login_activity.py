from django.db import models

from django.contrib.sessions.models import Session


class LoginActivity(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    device = models.CharField(blank=True, max_length=200)
    location = models.CharField(blank=True, max_length=200)
    os = models.CharField(blank=True, max_length=200)
    browser = models.CharField(blank=True, max_length=200)
    session = models.ForeignKey(Session, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name_plural = verbose_name = "تاریخچه ورود به حساب"