from django.db import models

from uuid import uuid4

# todo: maybe refactoring?


class Image(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

    def get_absolute_image_url(self):
        return self.image.url

    def __str__(self):
        return self.get_absolute_image_url()


class File(models.Model):
    uuid = models.UUIDField(default=uuid4, unique=True)
    file = models.FileField()
    
    def get_absolute_file_url(self):
        return self.file.url
    
    def __str__(self):
        return self.get_absolute_file_url()
    
    
