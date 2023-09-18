from django.db import models
from django.utils.text import slugify

import uuid
from tinymce.models import HTMLField

from multimedia.models import Image


class BaseItem(models.Model):
    title = models.CharField(max_length=30)
    title_en = models.CharField(max_length=30)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title_en)
        super().save(*args, **kwargs)


class Section(BaseItem):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True)
    icon = Image()
    description = models.TextField(blank=True)


class Article(BaseItem):
    uuid = models.UUIDField(default=uuid.uuid4(), editable=False)
    parent_section = models.ForeignKey(Section, on_delete=models.CASCADE)
    content = HTMLField()
