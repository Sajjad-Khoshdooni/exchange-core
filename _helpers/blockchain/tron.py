from random import choice
from tronpy.providers import HTTPProvider
from tronpy import Tron

_trons = []


def get_tron_client() -> Tron:
    global _trons
    if len(_trons) == 0:
        for api_key in ['bb149363-094b-47ad-8ed7-1bb42ac8541f',
                        '8a751720-2877-4d0e-8dc9-1c72ccff2ad8',
                        'd69566b0-4604-49b5-8066-d7441b3210ff']:
            provider = HTTPProvider(api_key=api_key)
            _trons.append(Tron(provider=provider))
    return choice(_trons)
