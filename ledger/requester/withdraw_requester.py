import requests
from yekta_config.config import config


class RequestWithdraw:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + config('BLOCKLINK_TOKEN')
        }

    def withdraw_from_hot_wallet(self, receiver_address, amount, network, asset, transfer_id):
        data = {
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': transfer_id  # todo: use transfer_id
        }

        url = config('BLOCKLINK_BASE_URL') + '/api/v1/withdraw/'

        return requests.post(data=data, url=url, headers=self.header)
