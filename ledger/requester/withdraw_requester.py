import requests
from yekta_config.config import config


class RequestWithdraw:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + config('BLOCKLINK_TOKEN')
        }

    def withdraw_from_hot_wallet(self, receiver_address, amount, network, asset, requester_id):
        data = {
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': requester_id
        }

        url = config('BLOCKLINK_BASE_URL') + config('BLOCKLINK_WITHDRAW_FROM_HOTWALLET')

        response = requests.post(data=data, url=url, headers=self.header).json()
        return response

    def withdraw_from_address(self, pointer_address, receiver_address, amount, network, asset, requester_id):
        data = {
            'pointer_address': pointer_address,
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': requester_id
        }

        url = config('BLOCKLINK_BASE_URL') + config('BLOCKLINK_WITHDRAW')
        response = requests.post(data=data, url=url, headers=self.header).json()
        return response
