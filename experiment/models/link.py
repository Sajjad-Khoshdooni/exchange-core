from django.db import models
from yekta_config.config import config

import string
import random


class Link(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=6, unique=True, db_index=True)
    destination = models.URLField(max_length=200)
    user = models.ForeignKey('accounts.user', on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    @classmethod
    def create(cls, user):
        token = cls.create_token()
        cls.objects.create(
            user=user,
            token=token,
            destination=config('EXPERIMENT_DEPOSIT_URL')
        )

    @staticmethod
    def create_token():
        while True:
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
            if not Link.objects.filter(token=token).first():
                return token

    def get_sms_link(self):
        return 'c.raastin.com/{token}'.format(token=self.token)
