import requests
from django.conf import settings


from ledger.utils.cache import cache_for


@cache_for(3600)
def request_architecture(network):
    data = {
        'network': network,
    }
    url = settings.BLOCKLINK_BASE_URL + '/api/v1/tracker/architecture/'
    header = {
        'Authorization': settings.BLOCKLINK_TOKEN
    }
    return requests.get(url=url, params=data, headers=header, timeout=10).json().get('architecture')
