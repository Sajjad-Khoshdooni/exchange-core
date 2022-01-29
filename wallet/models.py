from django.db import models
from eth_account import Account

from wallet.aes_cipher import secret_aes_cipher


class Secret(models.Model):
    encrypted_key = models.CharField(max_length=255, unique=True)

    @property
    def key(self):
        return secret_aes_cipher.decrypt(self.encrypted_key)

    @classmethod
    def build(cls):
        return cls.objects.create(
            encrypted_key=secret_aes_cipher.encrypt(Account.create().privateKey.hex())
        )


class ETHWallet(Secret):

    @property
    def address(self):
        return Account.from_key(self.key).address

    class Meta:
        proxy = True


class TRXWallet(Secret):
    @property
    def address(self):
        return '41' + Account.from_key(self.key).address[2:]

    class Meta:
        proxy = True
