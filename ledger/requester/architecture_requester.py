import requests
from yekta_config import secret
from yekta_config.config import config

from ledger.utils.cache import cache_for


@cache_for(3600)
def request_architecture(network):
    data = {
        'network': network,
    }
    url = config('BLOCKLINK_BASE_URL') + '/api/v1/tracker/architecture/'
    header = {
        'Authorization': secret('BLOCKLINK_TOKEN')
    }
    return requests.get(url=url, params=data, headers=header).json().get('architecture')
