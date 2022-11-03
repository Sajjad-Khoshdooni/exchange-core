from django.db import models

import string
import random


class Link(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=6, unique=True, db_index=True)
    destination = models.URLField(max_length=30)
    click = models.ForeignKey('experiment.Click', on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey('accounts.user', on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    @classmethod
    def create(cls, user):
        token = cls.create_token()
        destination = 'c.raastin.com/{token}'.format(token=token)
        cls.objects.create(
            user=user,
            token=token,
            destination=destination
        )

    @staticmethod
    def create_token():
        while True:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
            if not Link.objects.filter(token=token).first():
                return token
