from django.db import models

from accounts.models import Account
from wallet.models import Secret, CryptoWallet


class AccountSecret(models.Model):
    secret = models.ForeignKey(Secret, on_delete=models.PROTECT)
    account = models.OneToOneField(Account, on_delete=models.PROTECT)
    # type = models.CharField(max_length=1, choices=)

    def get_crypto_wallet(self, network) -> CryptoWallet:
        secret = self.secret
        secret.__class__ = Secret.get_secret_wallet(network.symbol)
        return secret

    def save(self, *args, **kwargs):
        if not self.id:
            self.secret = Secret.build()
            super(AccountSecret, self).save(*args, **kwargs)
        else:
            raise NotImplementedError

    def __str__(self):
        return str(self.account)
