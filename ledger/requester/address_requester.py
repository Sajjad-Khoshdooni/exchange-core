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
        url = config('MASTERKEY_BASE_URL') + '/api/v1/wallets/'
        res = requests.post(url=url, data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))

        return response['address']

    def generate_public_address(self, address, network: str):
        data = {
            "address": address,
            "network": network
        }
        url = config('MASTERKEY_BASE_URL') + '/api/v1/wallets/public/address/'
        resp = requests.get(url=url, data=data, headers=self.header)

        if not resp.ok:
            raise Exception('Failed to generate public address')

        return resp.json()['public_address']
