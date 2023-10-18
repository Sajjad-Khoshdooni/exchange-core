import uuid

from django.db import models
from django.utils.text import slugify
from django_quill.fields import QuillField

from multimedia.models import Image


class BaseItem(models.Model):
    title = models.TextField(max_length=256)
    title_en = models.TextField(max_length=256)
    slug = models.SlugField(max_length=1024, unique=True, db_index=True, blank=True)

    def __str__(self):
        return self.title


class Section(BaseItem):
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    icon = Image()
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'بخش'
        verbose_name_plural = 'بخش‌‌ها'
        ordering = ('order', 'id')


class Article(BaseItem):
    parent = models.ForeignKey(Section, on_delete=models.CASCADE)
    is_pinned = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    content = QuillField()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title_en + '-' + uuid.uuid4().hex)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'مقاله'
        verbose_name_plural = 'مقاله‌ها'
        ordering = ('order', 'id')
