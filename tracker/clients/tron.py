from random import choice

from tronpy.defaults import conf_for_name
from tronpy.providers import HTTPProvider
from tronpy import Tron

_tron_proxy = None


class TronProxy:
    def __init__(self, tron_list):
        self._tron_list = tron_list

    def __call__(self, *args, **kwargs):
        return choice(self._tron_list).__call__(*args, **kwargs)

    def __getattribute__(self, item):
        if item in ['_tron_list']:
            return super().__getattribute__(item)
        return getattr(choice(self._tron_list), item)


def get_tron_client(network='mainnet') -> Tron:
    global _tron_proxy
    _trons = []
    if _tron_proxy is None:
        for api_key in ['bb149363-094b-47ad-8ed7-1bb42ac8541f',
                        '8a751720-2877-4d0e-8dc9-1c72ccff2ad8',
                        'd69566b0-4604-49b5-8066-d7441b3210ff',
                        'edaa9d8d-0649-4425-910e-f15a1ca7632c',
                        'c6acfd07-cd72-4e33-bc69-550dcb7d7eba',
                        '1511f05b-a6cd-4ecd-a050-68c45b063a62',

                        'efb4acbb-2502-4ded-9083-fc9d86c10570',
                        '580cd15d-52fe-4516-af00-c84a4e176f83',
                        '8d510db0-a84d-47a1-9ad2-d65154792890'
                        ]:
            provider = HTTPProvider(endpoint_uri=conf_for_name(network), api_key=api_key,)
            _trons.append(Tron(provider=provider))
        _tron_proxy = TronProxy(_trons)
    return _tron_proxy


def validate_tron_trx(trx_hash):
    return get_tron_client().get_transaction(trx_hash)['ret'][0]['contractRet'] == 'SUCCESS'
