import requests
import logging
from django.conf import settings

from yekta_config import secret
from yekta_config.config import config

logger = logging.getLogger(__name__)


class InternalAssetsRequester:
    def __init__(self):
        self.url = config('BLOCKLINK_BASE_URL') + '/api/v1/hotwallet/amount/'
        self.header = {
            'Authorization': secret('BLOCKLINK_TOKEN')
        }

    def get_assets(self):
        resp = requests.get(url=self.url, headers=self.header)
        if not resp.ok:
            return None

        return resp.json()
