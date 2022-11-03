from django.db import models


class Click(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(max_length=500, blank=True)
    link = models.ForeignKey('experiment.Link', on_delete=models.CASCADE)
