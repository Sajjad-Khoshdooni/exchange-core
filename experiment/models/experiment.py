from django.db import models


class Experiment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20)
    active = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return self.name
