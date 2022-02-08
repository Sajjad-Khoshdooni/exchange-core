import requests
from web3 import Web3
from web3.middleware import geth_poa_middleware

_web3 = None

bscan = 'https://api.bscscan.com/'
# bscan = 'https://api-testnet.bscscan.com/'  # TESTNET

bscan_api_key = 'H78N3ND259DJINGK7A1SNMIWDA8EUMUMFG'


class BSC:
    def __init__(self):
        self._caches = {}

    def get_bsc_abi(self, contract_address: str) -> dict:
        if contract_address not in self._caches:
            url = f'{bscan}api?module=contract&action=getabi&address={contract_address}&apikey={bscan_api_key}'
            r = requests.get(url, headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
            })
            if not r.ok:
                raise Exception(f'Error getting ABI for contract {contract_address}')
            self._caches[contract_address] = r.json()['result']
        return self._caches[contract_address]


bsc = BSC()


def get_web3_bsc_client() -> Web3:
    global _web3
    if _web3 is None:
        bsc = 'https://bsc-dataseed.binance.org/'
        # bsc = 'https://data-seed-prebsc-1-s1.binance.org:8545/' # TESTNET
        _web3 = Web3(Web3.HTTPProvider(bsc))
        _web3.middleware_onion.inject(geth_poa_middleware, layer=0)
    return _web3
