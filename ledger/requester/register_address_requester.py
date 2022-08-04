import requests
import logging
from django.conf import settings

from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)


class RegisterAddress:
    def __init__(self):
        self.url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/address/'
        self.header = {
            'Authorization': secret('BLOCKLINK_TOKEN')
        }

    def register(self, deposit_address):
        if deposit_address.is_registered or settings.DEBUG_OR_TESTING:
            return

        data = {
            'pointer_address': deposit_address.address_key.address,
            'address': deposit_address.address,
            'network': deposit_address.network.symbol
        }

        resp = requests.post(url=self.url, headers=self.header, data=data)
        if not resp.ok:
            logger.warning('couldnt register deposit_address', extra={
                'address': deposit_address.address,
                'resp': resp.json(),
                'status': resp.status_code
            })
            print(resp.json())
            return
        deposit_address.is_registered = True
        deposit_address.save()
