import requests
from django.conf import settings
from decouple import config
from decouple import config


class RequestWithdraw:
    def __init__(self):
        self.header = {
            'Authorization': config('BLOCKLINK_TOKEN')
        }

    def withdraw_from_hot_wallet(self, receiver_address, amount, network, asset, transfer_id):
        if settings.DEBUG_OR_TESTING_OR_STAGING:
            return

        data = {
            'receiver_address': receiver_address,
            'amount': amount,
            'network': network,
            'coin': asset,
            'requester_id': transfer_id  # todo: use transfer_id
        }

        url = config('BLOCKLINK_BASE_URL', default='https://blocklink.raastin.com') + '/api/v1/withdraw/'

        return requests.post(data=data, url=url, headers=self.header)
