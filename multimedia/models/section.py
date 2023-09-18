from django.db import models
from django.utils.text import slugify

import uuid

from multimedia.models import Image


class Section(models.Model):
    parent_section = models.ForeignKey('self', on_delete=models.CASCADE, blank=True)

    icon = Image()
    title = models.CharField(max_length=30)
    title_en = models.CharField(max_length=30)

    description = models.TextField(blank=True)

    id = models.UUIDField(default=uuid.uuid4(), editable=False)
    slug = models.SlugField(max_length=255)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title_en)
        super().save(*args, **kwargs)

