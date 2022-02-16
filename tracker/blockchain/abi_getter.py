from abc import ABC, abstractmethod

import requests


class AbiGetter(ABC):

    @abstractmethod
    def from_contract(self, contract_str):
        pass


class BSCAbiGetter(AbiGetter):
    bscan = 'https://api.bscscan.com/'
    bscan_api_key = 'H78N3ND259DJINGK7A1SNMIWDA8EUMUMFG'

    # bscan = 'https://api-testnet.bscscan.com/'  # TESTNET
    def __init__(self):
        self._caches = {}

    def from_contract(self, contract_str):
        contract_address = '0x55d398326f99059ff775485246999027b3197955'  # NOTE: Some bep20 smart contract doesn't have
        # correct abis, so we use usdt abi for all smart contracts
        if contract_address not in self._caches:
            url = f'{self.bscan}api?module=contract&action=getabi&address={contract_address}&apikey={self.bscan_api_key}'
            r = requests.get(url, headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
            })
            if not r.ok:
                raise Exception(f'Error getting ABI for contract {contract_address}')
            self._caches[contract_address] = r.json()['result']
        return self._caches[contract_address]


class ETHAbiGetter(AbiGetter):
    scan = 'https://api.etherscan.io/'
    scan_api_key = 'B3FPGIPRK1QTTVRUZBT5RYKPYQ45WHDHM3'

    # bscan = 'https://api-testnet.etherscan.io/'  # TESTNET
    def __init__(self):
        self._caches = {}

    def from_contract(self, contract_address):
        if contract_address not in self._caches:
            url = f'{self.scan}api?module=contract&action=getabi&address={contract_address}&apikey={self.scan_api_key}'
            r = requests.get(url, headers={
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
            })
            if not r.ok:
                raise Exception(f'Error getting ABI for contract {contract_address}')
            self._caches[contract_address] = r.json()['result']
        return self._caches[contract_address]


bsc_abi_getter = BSCAbiGetter()
eth_abi_getter = ETHAbiGetter()
