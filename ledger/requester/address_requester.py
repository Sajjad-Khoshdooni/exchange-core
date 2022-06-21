import json
import random

import requests

from ledger.requester.consts import MASTERKEY_WALLET_URL, MASTERKEY_TOKEN, MASTERKEY_PUBLIC_ADDRESS_GENERATOR_URL
from django.conf import settings


class AddressRequester:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + MASTERKEY_TOKEN
        }

    def create_wallet(self):
        if settings.DEBUG_FAST_FORWARD:
            return '0xtest6Eb0c7Db0eAbbE8E04b9AF02C0b7212b' + str(random.randint(1000, 10000))
        data = {
            'tag': 'tag'
        }
        res = requests.post(url=MASTERKEY_WALLET_URL, data=data, headers=self.header)
        response = json.loads(res.content.decode('utf-8'))
        return response['address']

    def generate_public_address(self, address, network):
        data = {
            "address": address,
            "network": network
        }
        response = requests.get(url=MASTERKEY_PUBLIC_ADDRESS_GENERATOR_URL, data=data, headers=self.header)
        return response['public_address']
