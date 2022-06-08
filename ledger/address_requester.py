import json

import requests

from .consts import MASTERKEY_WALLET_URL


class AddressRequester:
    def __init__(self):
        self.url = MASTERKEY_WALLET_URL
        self.header = {
            'Authorization': 'Token ' + 'c22f401defb400ab345a9744d042573882e68ac7' # it shouldnt be hardcode
        }

    def create_wallet(self, network_symbol):
        data = {
            'tag': 'tag',
            'network': network_symbol
        }
        res = requests.post(url=self.url, data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))
        return response['address']
