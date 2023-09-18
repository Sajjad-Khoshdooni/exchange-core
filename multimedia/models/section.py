from django.db import models
from django.utils.text import slugify


from multimedia.models import Image


class Section(models.Model):
    parent_section = models.ForeignKey('self', on_delete=models.CASCADE, blank=True)
    title = models.CharField(max_length=30)
    title_en = models.CharField(max_length=30)
    icon = Image()
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super().save(*args, **kwargs)
