import requests
from yekta_config.config import config

from ledger.models import Transfer


class RequestWithdraw:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + config('BLOCKLINK_TOKEN')
        }

    def withdraw_from_hot_wallet(self, receiver_address, amount, network, asset):
        data = {
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': 1
        }

        response = requests.post(data=data, url=config('BLOCKLINK_WITHDRAW_FROM_HOTWALLET'), headers=self.header).json()
        return response

    def withdraw_from_address(self, pointer_address, receiver_address, amount, network, asset):
        data = {
            'pointer_address': pointer_address,
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': 1
        }

        response = requests.post(data=data, url=config('BLOCKLINK_WITHDRAW'), headers=self.header).json()
        return response
