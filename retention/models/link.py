import random
import string

from django.db import models

from experiment.utils.exceptions import TokenCreationError


def create_token():
    for i in range(0, 3):
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        if not Link.objects.filter(token=token).first():
            return token

    raise TokenCreationError


class Link(models.Model):
    SCOPE_DEPOSIT = 'd'
    SCOPE_CHOICES = ((SCOPE_DEPOSIT, 'deposit'), )

    SCOPE_TO_LINK = {
        SCOPE_DEPOSIT: '/wallet/spot/money-deposit?utm_source=raastin&utm_medium=sms&utm_campaign=1h-deposit',
    }

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    token = models.CharField(max_length=6, unique=True, db_index=True, default=create_token)

    scope = models.CharField(max_length=1, choices=SCOPE_CHOICES)
    user = models.ForeignKey('accounts.user', on_delete=models.CASCADE, related_name='%(class)s_requests_created')

    def get_link(self):
        return 'c.raastin.com/{token}'.format(token=self.token)

    def __str__(self):
        return '%s %s' % (self.user, self.scope)

    class Meta:
        unique_together = ('user', 'scope')
