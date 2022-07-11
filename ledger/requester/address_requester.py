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
        url = config('MASTERKEY_BASE_URL') + config('MASTERKEY_WALLET_URL')
        res = requests.post(url=url, data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))
        return response['address']

    def generate_public_address(self, address, network):
        data = {
            "address": address,
            "network": network
        }
        url = config('MASTERKEY_BASE_URL') + config('MASTERKEY_PUBLIC_ADDRESS_GENERATOR_URL')
        response = requests.get(url=url, data=data, headers=self.header).json()
        return response['public_address']
