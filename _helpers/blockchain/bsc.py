from web3 import Web3
from web3.middleware import geth_poa_middleware

_web3 = None


def get_web3_bsc_client() -> Web3:
    global _web3
    if _web3 is None:
        bsc = 'https://data-seed-prebsc-1-s1.binance.org:8545/'
        _web3 = Web3(Web3.HTTPProvider(bsc))
        _web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return _web3
