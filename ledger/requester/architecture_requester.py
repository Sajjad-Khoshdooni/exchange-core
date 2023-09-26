import requests
from django.conf import settings


from ledger.utils.cache import cache_for


@cache_for(3600)
def get_network_detail(network: str):
    if settings.DEBUG_OR_TESTING:
        if network == 'XRP':
            return {
                'architecture': 'XRP',
                'is_memo_base': True,
            }
        else:
            return {
                'architecture': 'ETH',
                'is_memo_base': False,
            }

    data = {
        'network': network,
    }
    url = settings.BLOCKLINK_BASE_URL + '/api/v1/tracker/architecture/'
    header = {
        'Authorization': settings.BLOCKLINK_TOKEN
    }
    return requests.get(url=url, params=data, headers=header, timeout=10).json()


def get_network_architecture(network: str):
    return get_network_detail(network).get('architecture')


def is_network_memo_base(network: str):
    return get_network_detail(network).get('is_memo_base', False)
