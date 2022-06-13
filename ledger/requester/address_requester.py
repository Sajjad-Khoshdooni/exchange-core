import json

import requests

from ledger.requester.consts import MASTERKEY_WALLET_URL, MASTERKEY_TOKEN


class AddressRequester:
    def __init__(self):
        self.url = MASTERKEY_WALLET_URL
        self.header = {
            'Authorization': 'Token ' + MASTERKEY_TOKEN
        }

    def create_wallet(self, network_symbol):
        data = {
            'tag': 'tag',
            'network': network_symbol
        }
        res = requests.post(url=self.url, data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))
        return response['address']
