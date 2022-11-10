from django.db import models

import string
import random

from experiment.utils.exceptions import TokenCreationError


def create_token():
    for i in range(0, 3):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        if not Link.objects.filter(token=token).first():
            return token

    raise TokenCreationError


class Link(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=6, unique=True, db_index=True, default=create_token)
    user = models.ForeignKey('accounts.user', on_delete=models.CASCADE, null=True, blank=True)

    @classmethod
    def create(cls, user):
        cls.objects.create(
            user=user,
        )

    def get_sms_link(self):
        return 'c.raastin.com/{token}'.format(token=self.token)

    def __str__(self):
        return self.get_sms_link()
