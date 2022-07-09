import requests
from yekta_config.config import config

from ledger.models import Transfer


class RequestWithdraw:
    def __init__(self):
        self.header = {
            'Authorization': 'Token ' + config('BLOCKLINK_TOKEN')
        }

    def withdraw_from_hot_wallet(self, transfer: Transfer):
        data = {
            'receiver_address': transfer.out_address,
            'amount': transfer.amount,
            'network': transfer.network,
            'coin': transfer.asset,
            'requester_id': 1
        }

        response = requests.post(data=data, url=config('BLOCKLINK_WITHDRAW_FROM_HOTWALLET'), headers=self.header).json()
        return response

    def withdraw_from_address(self, transfer: Transfer):
        data = {
            'pointer_address': transfer.deposit_address.address_key.address,
            'receiver_address': transfer.out_address,
            'amount': transfer.amount,
            'network': transfer.network,
            'coin': transfer.asset,
            'requester_id': 1
        }

        response = requests.post(data=data, url=config('BLOCKLINK_WITHDRAW'), headers=self.header).json()
        return response
