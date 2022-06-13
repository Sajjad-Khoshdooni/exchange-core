import requests
from rest_framework import request

from ledger.requester.consts import BLOCKLINK_TOKEN, BLOCKLINK_REGISTER_ADDRESS_URL
from ledger.models.deposit_address import DepositAddress


class RegisterAddress:
    def __init__(self):
        self.url = BLOCKLINK_REGISTER_ADDRESS_URL
        self.header = {
            'Authorization': 'Token ' + BLOCKLINK_TOKEN
        }

    def register(self, address, network):
        data = {
            'address': address,
            'network': network
        }

        res = requests.post(url=self.url, headers=self.header, data=data)
        if not res.ok:
            return
        deposit = DepositAddress.objects.filter(address=address)
        deposit.is_registered = True
        deposit.save()
