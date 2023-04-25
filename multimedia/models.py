from uuid import uuid4

from django.db import models
from simple_history.models import HistoricalRecords
from tinymce.models import HTMLField


class Image(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

    def get_absolute_image_url(self):
        return self.image.url

    def __str__(self):
        return self.get_absolute_image_url()


class Banner(models.Model):
    ONLY_DESKTOP = 'only_desktop'

    title = models.CharField(max_length=64)
    image = models.ImageField()
    link = models.CharField(max_length=256)
    app_link = models.CharField(max_length=256, blank=True)
    active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField()

    limit = models.CharField(
        max_length=16,
        blank=True,
        choices=((ONLY_DESKTOP, ONLY_DESKTOP), )
    )

    def __str__(self):
        return self.image.url

    class Meta:
        ordering = ('order', )


class CoinPriceContent(models.Model):
    asset = models.OneToOneField(to='ledger.Asset', on_delete=models.PROTECT)
    content = HTMLField()

    history = HistoricalRecords()

    def __str__(self):
        return str(self.asset)

    def get_html(self):
        return self.content.replace('\r\n', '')
