from typing import Type

from django.db import models
from eth_account import Account

from wallet.aes_cipher import secret_aes_cipher
from wallet.utils import get_base58_address


class CryptoWallet:

    @property
    def address(self):
        raise NotImplementedError

    @classmethod
    def get_presentation_address(cls, address: str):
        return address


class Secret(models.Model):
    encrypted_key = models.CharField(max_length=255, unique=True)

    @property
    def key(self):
        return secret_aes_cipher.decrypt(self.encrypted_key)

    @property
    def base16_address(self):
        return Account.from_key(self.key).address[2:].lower()

    @classmethod
    def build(cls):
        return cls.objects.create(
            encrypted_key=secret_aes_cipher.encrypt(Account.create().privateKey.hex()).decode()
        )

    @staticmethod
    def get_secret_wallet(network: str) -> Type['Secret']:
        wallet_map = {
            'ETH': ETHWallet,
            'TRX': TRXWallet
        }
        return wallet_map[network]


class ETHWallet(Secret, CryptoWallet):

    @property
    def address(self):
        return '0x' + self.base16_address

    class Meta:
        proxy = True


class TRXWallet(Secret, CryptoWallet):

    @property
    def address(self):
        return '41' + super().base16_address

    @classmethod
    def get_presentation_address(cls, address: str):
        return get_base58_address(address)

    class Meta:
        proxy = True
