import json
import requests
from django.conf import settings
from yekta_config import secret
from yekta_config.config import config

from ledger.utils.cache import cache_for


class ArchitectureRequester:
    @cache_for(3600)
    @classmethod
    def request_architecture(cls, network):
        data = {
            'network': network,
        }
        url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/architecture/'
        header = {
            'Authorization': secret('BLOCKLINK_TOKEN')
        }
        return requests.get(url=url, params=data, headers=header).json().get('architecture')
