import json
import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config


class AddressRequester:
    def __init__(self):
        self.header = {
            'Authorization': secret('MASTERKEY_TOKEN')
        }

    def create_wallet(self, account):
        data = {
            'tag': '{brand}-base-{account_id}'.format(
                brand=settings.BRAND_EN.lower(),
                account_id=account.id,
            )
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
