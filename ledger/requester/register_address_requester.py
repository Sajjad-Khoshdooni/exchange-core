import requests
import logging
from ledger.requester.consts import BLOCKLINK_TOKEN, BLOCKLINK_REGISTER_ADDRESS_URL
from ledger.models.deposit_address import DepositAddress

logger = logging.getLogger(__name__)


class RegisterAddress:
    def __init__(self):
        self.url = BLOCKLINK_REGISTER_ADDRESS_URL
        self.header = {
            'Authorization': 'Token ' + BLOCKLINK_TOKEN
        }

    def register(self, deposit_address: DepositAddress):
        if deposit_address.is_registered:
            return

        data = {
            'address': deposit_address.address,
            'network': deposit_address.network.symbol
        }

        res = requests.post(url=self.url, headers=self.header, data=data)
        if not res.ok:
            logger.warning('couldnt register deposit_address: {} in blocklink'.format(deposit_address.address))
            return
        deposit_address.is_registered = True
        deposit_address.save()
