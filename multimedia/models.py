from uuid import uuid4

from django.db import models


class Image(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

