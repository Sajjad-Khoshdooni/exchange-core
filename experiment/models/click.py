from django.db import models


class Click(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    user_agent = models.CharField(max_length=500)
