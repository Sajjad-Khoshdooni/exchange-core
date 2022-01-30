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
            encrypted_key=secret_aes_cipher.encrypt(Account.create().privateKey.hex()).decode()
        )

    @staticmethod
    def get_secret_wallet(network: str):
        wallet_map = {
            'ETH': ETHWallet,
            'TRX': TRXWallet
        }
        return wallet_map[network]


class ETHWallet(Secret):

    @property
    def address(self):
        return Account.from_key(self.key).address.lower()

    class Meta:
        proxy = True


class TRXWallet(Secret):
    TRX_ADDRESS_PREFIX = '41'

    @property
    def address(self):
        return self.TRX_ADDRESS_PREFIX + Account.from_key(self.key).address[2:].lower()

    class Meta:
        proxy = True
