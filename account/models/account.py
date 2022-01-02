from django.db import models
from account.models import User


class Account(models.Model):
    SYSTEM = 's'
    OUT = 'o'
    ORDINARY = ''

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)

    type = models.CharField(
        max_length=1,
        choices=((SYSTEM, 'system'), (OUT, 'out'), (ORDINARY, 'ordinary')),
        blank=True
    )

    @classmethod
    def system(cls) -> 'Account':
        return Account.objects.get(type=cls.SYSTEM)

    @classmethod
    def out(cls) -> 'Account':
        return Account.objects.get(type=cls.OUT)

    def __str__(self):
        if self.type == self.SYSTEM:
            return 'system'
        elif self.type == self.OUT:
            return 'out'
        else:
            return str(self.user)

    def save(self, *args, **kwargs):
        super(Account, self).save(*args, **kwargs)

        if self.type and self.user:
            raise Exception('User connected to system account')
