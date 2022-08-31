import requests
import logging
from django.conf import settings

from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)


class UpdateTrxHistory:
    def __init__(self):
        self.url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/address/update/'
        self.header = {
            'Authorization': secret('BLOCKLINK_TOKEN')
        }

    def update_history(self, deposit_address):
        if deposit_address.network.symbol != 'SOL':
            return
        data = {
            'pointer_address': deposit_address.address_key.address,
            'address': deposit_address.address,
            'network': deposit_address.network.symbol
        }

        requests.put(url=self.url, headers=self.header, data=data)
