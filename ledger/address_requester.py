import requests

from accounts.models.account import Account

from .consts import MASTERKEY_WALLET_URL


class AddressRequester:
    def __init__(self):
        self.url = MASTERKEY_WALLET_URL
        self.header = {
            'Content-Type': 'Application/json'
        }

    def create_wallet(self, account:Account):
        data = {
            'tag': 'tag'
        }
        res = requests.post(url=self.url, data=data, headers=self.header)
        res = res.content.decode('utf-8')
        return res['address']
