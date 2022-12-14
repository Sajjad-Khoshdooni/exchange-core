import requests
from decouple import config
from decouple import config

from ledger.utils.cache import cache_for


@cache_for(3600)
def request_architecture(network):
    data = {
        'network': network,
    }
    url = config('BLOCKLINK_BASE_URL', default='https://blocklink.raastin.com') + '/api/v1/tracker/architecture/'
    header = {
        'Authorization': config('BLOCKLINK_TOKEN')
    }
    return requests.get(url=url, params=data, headers=header, timeout=10).json().get('architecture')
