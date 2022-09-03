from uuid import uuid4

from django.conf import settings
from django.db import models


class Image(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

    def get_absolute_image_url(self):
        return settings.HOST_URL + self.image.url

    def __str__(self):
        return self.get_absolute_image_url()


class Banner(models.Model):
    title = models.CharField(max_length=64)
    image = models.ImageField()
    link = models.URLField()
    active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField()

    def get_absolute_image_url(self):
        return settings.HOST_URL + self.image.url

    def __str__(self):
        return self.get_absolute_image_url()

    class Meta:
        ordering = ('order', )
