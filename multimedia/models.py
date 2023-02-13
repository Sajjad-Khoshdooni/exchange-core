from uuid import uuid4

from django.conf import settings
from django.db import models
from django_quill.fields import QuillField
from tinymce.models import HTMLField

class Image(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

    def get_absolute_image_url(self):
        return self.image.url

    def __str__(self):
        return self.get_absolute_image_url()


class Banner(models.Model):
    title = models.CharField(max_length=64)
    image = models.ImageField()
    link = models.CharField(max_length=256)
    app_link = models.CharField(max_length=256, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.image.url

    class Meta:
        ordering = ('order', )


class CoinPriceContent(models.Model):
    asset = models.OneToOneField(to='ledger.Asset', on_delete=models.PROTECT)
    content = HTMLField()

    def __str__(self):
        return str(self.asset)
