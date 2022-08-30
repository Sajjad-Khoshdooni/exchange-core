import json
import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config


class AddressRequester:
    def create_wallet(self, account, architecture):
        data = {
            'architecture': architecture,
            'tag': '{brand}-base-{account_id}'.format(
                brand=settings.BRAND_EN.lower(),
                account_id=account.id,
            )
        }
        url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/wallets/'
        header = {
            'Authorization': secret('BLOCKLINK_TOKEN')
        }
        return requests.post(url=url, data=data, headers=header).json()

    def generate_public_address(self, address, network: str):
        data = {
            "address": address,
            "network": network
        }
        url = config('MASTERKEY_BASE_URL') + '/api/v1/wallets/public/address/'
        header = {
            'Authorization': secret('MASTERKEY_TOKEN')
        }
        resp = requests.get(url=url, data=data, headers=header)

        if not resp.ok:
            raise Exception('Failed to generate public address')

        return resp.json()['public_address']