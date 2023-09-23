import uuid

from django.db import models
from django.utils.text import slugify
from django_quill.fields import QuillField

from multimedia.models import Image


class BaseItem(models.Model):
    title = models.TextField(max_length=30)
    title_en = models.TextField(max_length=30)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, editable=False)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title_en + '-' + str(uuid.uuid4()))
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Section(BaseItem):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    icon = Image()
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'بخش'
        verbose_name_plural = 'بخش‌ ها'


class Article(BaseItem):
    parent_section = models.ForeignKey(Section, on_delete=models.CASCADE)
    is_pinned = models.BooleanField(default=False)
    content = QuillField()

    class Meta:
        verbose_name = 'مقاله'
        verbose_name_plural = 'مقاله ها'
