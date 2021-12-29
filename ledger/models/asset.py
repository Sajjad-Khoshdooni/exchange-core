from django.db import models


class Asset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)
    image = models.FileField(upload_to='asset-logo/')
