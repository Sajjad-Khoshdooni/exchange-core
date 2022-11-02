import requests
import logging
from django.conf import settings

from decouple import config
from decouple import config

logger = logging.getLogger(__name__)


class InternalAssetsRequester:
    def __init__(self):
        self.url = config('BLOCKLINK_BASE_URL', default='https://blocklink.raastin.com') + '/api/v1/hotwallet/amount/'
        self.header = {
            'Authorization': config('BLOCKLINK_TOKEN')
        }

    def get_assets(self):

        if settings.DEBUG_OR_TESTING_OR_STAGING:
            return []

        resp = requests.get(url=self.url, headers=self.header)
        if not resp.ok:
            return None

        return resp.json()
