import uuid

from django.db import models
from django.utils.text import slugify
from django_quill.fields import QuillField


class BaseItem(models.Model):
    title = models.TextField(max_length=256)
    title_en = models.TextField(max_length=256)
    slug = models.SlugField(max_length=1024, unique=True, db_index=True, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        abstract = True


class Section(BaseItem):
    ICONS = 'getting-started', 'signup', 'accounts', 'transfer', 'trade', 'earn'

    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    icon = models.CharField(max_length=256, blank=True, choices=[(i, i) for i in ICONS])

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
