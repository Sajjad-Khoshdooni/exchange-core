from django.db import models

from accounts.models import Notification


class Template(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    content = models.TextField(null=True)
    target = models.CharField(
        max_length=8,
        choices=Notification.TARGET_SOURCE,
        default=Notification.SYSTEM
    )
