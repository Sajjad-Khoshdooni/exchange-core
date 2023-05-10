from django.db import models


class Click(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField(blank=True)
    link = models.ForeignKey('retention.Link', on_delete=models.CASCADE)
