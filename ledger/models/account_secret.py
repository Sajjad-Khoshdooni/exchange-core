from django.db import models

from accounts.models import Account
from wallet.models import Secret


class AccountSecret(models.Model):

    secret = models.ForeignKey(Secret, on_delete=models.PROTECT)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, unique=True)
    # type = models.CharField(max_length=1, choices=)

    def save(self, *args, **kwargs):
        if not self.id:
            self.secret = Secret.build()
            super(AccountSecret, self).save(*args, **kwargs)
        else:
            raise NotImplementedError

    def __str__(self):
        return str(self.account)
