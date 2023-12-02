from django.db import models

from uuid import uuid4


class Image(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid4, unique=True)
    image = models.ImageField()

    def get_absolute_image_url(self):
        return self.image.url

    def __str__(self):
        return f'Image {self.id}'


class File(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(default=uuid4, unique=True)
    file = models.FileField()
    
    def get_absolute_file_url(self):
        return self.file.url
    
    def __str__(self):
        return f'File {self.id}'
