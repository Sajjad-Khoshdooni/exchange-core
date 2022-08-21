from django.db import models


class AppTrackerCode(models.Model):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=64)
