from django.db import models

from accounts.models import User


class UserComment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(
        verbose_name='نظر'
    )

    class Meta:
        verbose_name = "نظر کاربر"
        verbose_name_plural = "نظر‌های کاربر"




