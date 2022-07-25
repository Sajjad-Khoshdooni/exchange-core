import requests
import logging
from yekta_config.config import config

logger = logging.getLogger(__name__)


class RegisterAddress:
    def __init__(self):
        self.url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/address/'
        self.header = {
            'Authorization': 'Token ' + config('BLOCKLINK_TOKEN')
        }

    def register(self, deposit_address):
        if deposit_address.is_registered:
            return

        data = {
            'pointer_address': deposit_address.address_key.address,
            'address': deposit_address.address,
            'network': deposit_address.network.symbol
        }

        res = requests.post(url=self.url, headers=self.header, data=data)
        if not res.ok:
            logger.warning('couldnt register deposit_address: {} in blocklink'.format(deposit_address.address))
            return
        deposit_address.is_registered = True
        deposit_address.save()
