import json

_addresses = {}


def get_addresses(network: str) -> list:
    assert network == 'eth'

    addresses = _addresses.get(network)

    if not addresses:
        with open('../addresses/%s.json' % network) as f:
            addresses = json.load(f)
            _addresses[network] = addresses

    return addresses


def get_network_address(network: str, index: int):
    return get_addresses(network)[index]
