import json
import requests
from yekta_config.config import config


class AddressRequester:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + config('MASTERKEY_TOKEN')
        }

    def create_wallet(self):
        data = {
            'tag': 'tag'
        }
        res = requests.post(url=config('MASTERKEY_WALLET_URL'), data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))
        return response['address']

    def generate_public_address(self, address, network):
        data = {
            "address": address,
            "network": network
        }
        response = requests.get(url=config('MASTERKEY_PUBLIC_ADDRESS_GENERATOR_URL'), data=data, headers=self.header)
        return response['public_address']
