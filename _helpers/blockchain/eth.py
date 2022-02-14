import web3
from web3 import Web3
from web3.middleware import geth_poa_middleware

_web3 = None


def get_web3_eth_client() -> Web3:
    global _web3
    if _web3 is None:
        _web3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/3befd24cf53a4f889d632c3293c36d3e'))
        _web3.middleware_onion.add(web3.middleware.gas_price_strategy_middleware)
        _web3.middleware_onion.add(web3.middleware.buffered_gas_estimate_middleware)
    return _web3
