import uuid

from django.db import models
from django.utils.text import slugify
from django_quill.fields import QuillField

from multimedia.models import Image


class BaseItem(models.Model):
    title = models.CharField(max_length=30)
    title_en = models.CharField(max_length=30)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title_en)
        super().save(*args, **kwargs)


class Section(BaseItem):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    icon = Image()
    description = models.TextField(blank=True)

    def __str__(self):
        return self.title


class Article(BaseItem):
    uuid = models.UUIDField(default=uuid.uuid4(), editable=False)
    parent_section = models.ForeignKey(Section, on_delete=models.CASCADE)
    is_pinned = models.BooleanField(default=False)
    content = QuillField()
