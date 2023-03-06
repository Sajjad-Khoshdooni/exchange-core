import requests
import logging

from django.conf import settings


logger = logging.getLogger(__name__)


class InternalAssetsRequester:
    def __init__(self):
        self.url = settings.BLOCKLINK_BASE_URL + '/api/v1/hotwallet/amount/'
        self.header = {
            'Authorization': settings.BLOCKLINK_TOKEN
        }

    def get_assets(self):

        if settings.DEBUG_OR_TESTING_OR_STAGING:
            return []

        resp = requests.get(url=self.url, headers=self.header, timeout=10)
        if not resp.ok:
            return None

        return resp.json()
